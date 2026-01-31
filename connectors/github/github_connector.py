"""GitHub API connector for listing and fetching repository file contents."""
import base64
from typing import List, Dict, Any, Optional
import requests

GITHUB_API_BASE = "https://api.github.com"
# Text/markdown extensions to ingest; skip binary
SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc", ".asciidoc", ".json", ".yaml", ".yml", ".pdf", ".docx", ".xlsx" }


class GitHubConnector:
    """List and fetch file contents from a GitHub repository (public repos, no auth)."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"token {token}"
        self.session.headers.setdefault("Accept", "application/vnd.github.v3+json")

    def list_path(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main",
    ) -> List[Dict[str, Any]]:
        """List contents of a path (files and dirs). One level only."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return [data]
        return data

    def _list_files_via_tree(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
        limit: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Use Git Trees API to get full recursive tree, then filter to path. One API call for commit + tree."""
        path = path.strip("/")
        prefix = path + "/" if path and path != "." else ""
        prefix_lower = prefix.lower()
        # Get commit for ref (branch/tag), then its tree SHA (required for git/trees, not commit SHA)
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{ref}"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        commit_resp = r.json()
        tree_sha = (commit_resp.get("commit") or {}).get("tree")
        if isinstance(tree_sha, dict):
            tree_sha = tree_sha.get("sha")
        if not tree_sha:
            tree_sha = commit_resp.get("sha")  # fallback
        if not tree_sha:
            return []
        # Get full tree recursively (tree_sha is the tree object SHA, not commit SHA)
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{tree_sha}"
        r = self.session.get(url, params={"recursive": "1"}, timeout=30)
        r.raise_for_status()
        tree = r.json()
        if tree.get("truncated"):
            # Tree was truncated (repo very large); fallback will be used by list_files_recursive
            raise ValueError("Tree truncated")
        entries = tree.get("tree") or []
        out: List[Dict[str, Any]] = []
        for entry in entries:
            if entry.get("type") != "blob":
                continue
            file_path = entry.get("path", "")
            if path and path != ".":
                # Match path prefix case-insensitively (e.g. novatech-kb vs Novatech-KB)
                fp_lower = file_path.lower()
                if fp_lower != path.lower() and not fp_lower.startswith(prefix_lower):
                    continue
            name = file_path.split("/")[-1]
            if any(name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                out.append({"path": file_path, "name": name, "type": "file", "sha": entry.get("sha")})
                if limit is not None and len(out) >= limit:
                    break
        return out

    def _list_files_via_contents_walk(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
        limit: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Walk directory tree via Contents API (one level per call). Guarantees full recursion into subdirs."""
        out: List[Dict[str, Any]] = []
        stack = [path]
        while stack and (limit is None or len(out) < limit):
            current = stack.pop()
            try:
                items = self.list_path(owner, repo, current, ref)
            except Exception:
                continue
            for item in items:
                print("DISCOVERED:", item.get("path"), item.get("type"))
                if item.get("type") == "dir":
                    stack.append(item["path"])
                elif item.get("type") == "file":
                    name = item.get("name", "")
                    if any(name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        # Contents API returns path and name
                        out.append({
                            "path": item.get("path", f"{current.rstrip('/')}/{name}"),
                            "name": name,
                            "type": "file",
                            "sha": item.get("sha"),
                        })
                    if limit is not None and len(out) >= limit:
                        break
        return out

    def list_files_recursive(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main",
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List all files under path recursively (including all subfolders).
        For a specific path (e.g. novatech-kb) uses Contents API walk so every subdir is listed.
        For full repo (path empty or '.') uses Git Trees API for efficiency."""
        path = path.strip("/") or "."
        # For a single directory path, use Contents API walk so we definitely get all nested files
        if path != ".":
            return self._list_files_via_contents_walk(owner, repo, path, ref, limit)
        # Full repo: use Tree API (one recursive call)
        try:
            return self._list_files_via_tree(owner, repo, ".", ref, limit)
        except Exception:
            pass
        return self._list_files_via_contents_walk(owner, repo, ".", ref, limit)

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main",
    ) -> Dict[str, Any]:
        """Fetch file content. Returns dict with content (str), path, name, encoding.
        For PDF/binary files also returns content_bytes so ingestion can extract text."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        content_b64 = data.get("content")
        name = data.get("name", path.split("/")[-1])
        out = {
            "content": "",
            "path": data.get("path", path),
            "name": name,
            "encoding": data.get("encoding", "base64"),
        }
        if not content_b64:
            return out
        raw_bytes = base64.b64decode(content_b64)
        # PDF (and .md.pdf) and other binary: return bytes for text extraction in ingestion
        if path.lower().endswith(".pdf") or name.lower().endswith(".pdf"):
            out["content_bytes"] = raw_bytes
            return out
        try:
            out["content"] = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass
        return out
