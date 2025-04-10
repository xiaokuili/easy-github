import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
import tempfile
import subprocess
import base64

@dataclass
class FileNode:
    """表示文件系统中的一个节点（文件或目录）"""
    path: str
    is_dir: bool
    children: List['FileNode'] = None
    content: str = None
    language: str = None

class GitHub:
    """
    GitHub项目分析类（精简版）
    仅保留元数据、文件树和README获取功能
    """
    
    def __init__(self):
        self.repo_url = None
        self.repo_name = None
        self.repo_owner = None
        self.root_dir = None
        self.file_tree = None
        self.repo_info = {}
        
    def load_repo_from_url(self, url: str) -> bool:
        """从GitHub URL加载项目"""
        self.repo_url = url
        
        # 解析URL获取仓库所有者和名称
        if url.startswith('git@github.com:'):
            parts = url.split(':')[1].split('/')
            if len(parts) < 2:
                return False
            self.repo_owner = parts[0]
            self.repo_name = parts[1].replace('.git', '')
        else:
            parts = url.strip('/').split('/')
            if len(parts) < 5 or parts[2] != 'github.com':
                return False
            self.repo_owner = parts[3]
            self.repo_name = parts[4]
        
        self._fetch_repo_metadata()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.root_dir = temp_dir
            try:
                subprocess.run(
                    ['git', 'clone', url, temp_dir],
                    check=True, 
                    capture_output=True,
                    env=os.environ
                )
                self.file_tree = self._build_file_tree(temp_dir)
                return True
            except Exception as e:
                print(f"Failed to load repository: {e}")
                return False
    
    def _fetch_repo_metadata(self):
        """获取GitHub仓库的元数据信息"""
        api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                self.repo_info = {
                    "name": data.get("name"),
                    "full_name": data.get("full_name"),
                    "description": data.get("description"),
                    "stars": data.get("stargazers_count"),
                    "forks": data.get("forks_count"),
                    "language": data.get("language"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "owner": {
                        "login": data.get("owner", {}).get("login"),
                        "avatar_url": data.get("owner", {}).get("avatar_url"),
                    }
                }
                
                # 获取README内容
                readme_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/readme"
                readme_response = requests.get(readme_url)
                if readme_response.status_code == 200:
                    readme_data = readme_response.json()
                    readme_content = readme_data.get("content", "")
                    if readme_content:
                        self.repo_info["readme"] = base64.b64decode(readme_content).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Failed to fetch repository metadata: {e}")
    
    def get_repo_info(self) -> Dict:
        """获取仓库详细信息"""
        return {
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "repo_owner": self.repo_owner,
            **self.repo_info
        }
    
    def get_file_tree(self, max_depth: int = None) -> FileNode:
        """获取项目文件树结构"""
        if max_depth is None:
            return self.file_tree
        return self._get_tree_with_depth(self.file_tree, max_depth)
    
    def _get_tree_with_depth(self, node: FileNode, max_depth: int, current_depth: int = 0) -> FileNode:
        """获取指定深度的文件树"""
        if current_depth >= max_depth:
            return FileNode(
                path=node.path,
                is_dir=node.is_dir,
                children=[] if node.is_dir else None,
                content=None,
                language=node.language
            )
        
        new_node = FileNode(
            path=node.path,
            is_dir=node.is_dir,
            children=[] if node.is_dir else None,
            content=node.content,
            language=node.language
        )
        
        if node.is_dir and node.children:
            for child in node.children:
                new_child = self._get_tree_with_depth(child, max_depth, current_depth + 1)
                new_node.children.append(new_child)
        
        return new_node
    
    def _build_file_tree(self, root_path: str) -> FileNode:
        """构建项目文件树"""
        root = FileNode(path=root_path, is_dir=True, children=[])
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            if '.git' in dirpath:
                continue
                
            current_dir = self._get_or_create_node(root, dirpath)
            
            for dirname in dirnames:
                if dirname.startswith('.'):
                    continue
                dir_node = FileNode(
                    path=os.path.join(dirpath, dirname),
                    is_dir=True,
                    children=[]
                )
                current_dir.children.append(dir_node)
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                file_path = os.path.join(dirpath, filename)
                language = self._detect_language(file_path)
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_node = FileNode(
                    path=file_path,
                    is_dir=False,
                    content=content,
                    language=language
                )
                current_dir.children.append(file_node)
                
        return root
    
    def _get_or_create_node(self, root: FileNode, path: str) -> FileNode:
        """获取或创建文件树中的节点"""
        if root.path == path:
            return root
            
        parts = os.path.relpath(path, root.path).split(os.sep)
        current = root
        
        for part in parts:
            if part == '.':
                continue
                
            found = False
            for child in current.children:
                if os.path.basename(child.path) == part and child.is_dir:
                    current = child
                    found = True
                    break
                    
            if not found:
                new_path = os.path.join(current.path, part)
                new_node = FileNode(path=new_path, is_dir=True, children=[])
                current.children.append(new_node)
                current = new_node
                
        return current
    
    def _detect_language(self, file_path: str) -> str:
        """检测文件语言类型"""
        ext = os.path.splitext(file_path)[1].lower()
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.html': 'HTML',
            '.css': 'CSS',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.yml': 'YAML',
            '.yaml': 'YAML',
        }
        return language_map.get(ext, 'Unknown')

if __name__ == "__main__":
    github = GitHub()
    repo_url = "git@github.com:ahmedkhaleel2004/gitdiagram.git"
    
    if github.load_repo_from_url(repo_url):
        # 获取并打印仓库信息
        repo_info = github.get_repo_info()
        print(f"仓库名称: {repo_info['full_name']}")
        print(f"描述: {repo_info['description']}")
        print(f"星数: {repo_info['stars']}")
        print(f"主要语言: {repo_info['language']}")
        
        # 获取并打印README
        if 'readme' in repo_info:
            print("\nREADME内容:")
            print(repo_info['readme'][:500] + "...")  # 只打印前500字符
        
        # 获取并打印文件树
        file_tree = github.get_file_tree(max_depth=2)
        print("\n文件树结构 (深度限制为2层):")
        
        def print_node(node, level=0):
            indent = "  " * level
            if node.is_dir:
                print(f"{indent}📁 {os.path.basename(node.path)}")
                if node.children:
                    for child in node.children:
                        print_node(child, level + 1)
            else:
                print(f"{indent}📄 {os.path.basename(node.path)} ({node.language})")
        
        print_node(file_tree)
    else:
        print("仓库加载失败")