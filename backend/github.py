import os
import requests
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import tempfile
import subprocess
import json
import re




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
    GitHub项目分析类
    
    用于获取GitHub项目的结构和依赖关系，提供核心数据访问API
    """
    
    def __init__(self):
        self.repo_url = None
        self.repo_name = None
        self.repo_owner = None
        self.root_dir = None
        self.file_tree = None
        self.dependency_map = {}
        self.third_party_deps = {}  # 存储第三方依赖
        self.repo_info = {}
        self.project_files = set()  # 存储项目中的所有文件路径
        
    def load_repo_from_url(self, url: str) -> bool:
        """
        从GitHub URL加载项目
        
        Args:
            url: GitHub项目URL，支持https和git@格式
            
        Returns:
            bool: 加载是否成功
        """
        self.repo_url = url
        
        # 解析URL获取仓库所有者和名称
        if url.startswith('git@github.com:'):
            # 处理git@github.com:owner/repo.git格式
            parts = url.split(':')[1].split('/')
            if len(parts) < 2:
                return False
            self.repo_owner = parts[0]
            self.repo_name = parts[1].replace('.git', '')
        else:
            # 处理https://github.com/owner/repo格式
            parts = url.strip('/').split('/')
            if len(parts) < 5 or parts[2] != 'github.com':
                return False
            self.repo_owner = parts[3]
            self.repo_name = parts[4]
        
        # 获取仓库基本信息
        self._fetch_repo_metadata()
        
        # 创建临时目录并克隆仓库
        with tempfile.TemporaryDirectory() as temp_dir:
            self.root_dir = temp_dir
            try:
                subprocess.run(
                    ['git', 'clone', url, temp_dir],
                    check=True, 
                    capture_output=True,
                    env=os.environ  # 继承全部环境变量
                )
                # 构建文件树
                self.file_tree = self._build_file_tree(temp_dir)
                # 收集项目中的所有文件路径
                self._collect_project_files(self.file_tree)
                # 分析项目依赖
                self._analyze_dependencies()
                return True
            except Exception as e:
                print(f"Failed to load repository: {e}")
                return False
    
    def _collect_project_files(self, node: FileNode):
        """收集项目中的所有文件路径"""
        if not node.is_dir:
            rel_path = os.path.relpath(node.path, self.root_dir)
            module_path = os.path.splitext(rel_path)[0].replace(os.sep, '.')
            self.project_files.add(module_path)
        elif node.children:
            for child in node.children:
                self._collect_project_files(child)
    
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
                        import base64
                        self.repo_info["readme"] = base64.b64decode(readme_content).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Failed to fetch repository metadata: {e}")
    
    def get_repo_info(self) -> Dict:
        """
        获取仓库详细信息
        
        Returns:
            Dict: 包含仓库名称、所有者、星数、语言等详细信息
        """
        return {
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "repo_owner": self.repo_owner,
            **self.repo_info
        }
    
    def get_file_tree(self, max_depth: int = None) -> FileNode:
        """
        获取项目文件树结构，可以指定最大深度
        
        Args:
            max_depth: 最大深度，None表示不限制
            
        Returns:
            FileNode: 文件树根节点
        """
        if max_depth is None:
            return self.file_tree
        else:
            return self._get_tree_with_depth(self.file_tree, max_depth)
    
    def _get_tree_with_depth(self, node: FileNode, max_depth: int, current_depth: int = 0) -> FileNode:
        """获取指定深度的文件树"""
        if current_depth >= max_depth:
            # 达到最大深度，返回没有子节点的副本
            return FileNode(
                path=node.path,
                is_dir=node.is_dir,
                children=[] if node.is_dir else None,
                content=None,
                language=node.language
            )
        
        # 创建当前节点的副本
        new_node = FileNode(
            path=node.path,
            is_dir=node.is_dir,
            children=[] if node.is_dir else None,
            content=node.content,
            language=node.language
        )
        
        # 递归处理子节点
        if node.is_dir and node.children:
            for child in node.children:
                new_child = self._get_tree_with_depth(child, max_depth, current_depth + 1)
                new_node.children.append(new_child)
        
        return new_node
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """
        获取指定文件的项目内部导入依赖
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[str]: 项目内部导入依赖列表
        """
        all_deps = self.dependency_map.get(file_path, [])
        # 只返回项目内部依赖
        return [dep for dep in all_deps if self._is_project_dependency(dep)]
    
    def get_file_third_party_dependencies(self, file_path: str) -> List[str]:
        """
        获取指定文件的第三方导入依赖
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[str]: 第三方导入依赖列表
        """
        all_deps = self.dependency_map.get(file_path, [])
        # 只返回第三方依赖
        return [dep for dep in all_deps if not self._is_project_dependency(dep)]
    
    def _is_project_dependency(self, import_line: str) -> bool:
        """判断导入语句是否为项目内部依赖"""
        if import_line.startswith('import '):
            module = import_line[7:].split()[0].split('.')[0]
            return module in self.project_files
        elif import_line.startswith('from '):
            parts = import_line[5:].split()
            if len(parts) >= 2 and parts[1] == 'import':
                module = parts[0].split('.')[0]
                return module in self.project_files
        return False
    
    def get_all_dependencies(self) -> Dict[str, List[str]]:
        """
        获取项目中所有文件的项目内部导入依赖关系
        
        Returns:
            Dict[str, List[str]]: 文件路径到项目内部导入依赖列表的映射
        """
        result = {}
        for file_path, deps in self.dependency_map.items():
            project_deps = [dep for dep in deps if self._is_project_dependency(dep)]
            if project_deps:  # 只包含有项目内部依赖的文件
                result[file_path] = project_deps
        return result
    
    def get_all_third_party_dependencies(self) -> Dict[str, List[str]]:
        """
        获取项目中所有文件的第三方导入依赖关系
        
        Returns:
            Dict[str, List[str]]: 文件路径到第三方导入依赖列表的映射
        """
        result = {}
        for file_path, deps in self.dependency_map.items():
            third_party_deps = [dep for dep in deps if not self._is_project_dependency(dep)]
            if third_party_deps:  # 只包含有第三方依赖的文件
                result[file_path] = third_party_deps
        return result
    
    def _build_file_tree(self, root_path: str) -> FileNode:
        """构建项目文件树"""
        root = FileNode(path=root_path, is_dir=True, children=[])
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # 跳过.git目录
            if '.git' in dirpath:
                continue
                
            current_dir = self._get_or_create_node(root, dirpath)
            
            # 添加子目录
            for dirname in dirnames:
                if dirname.startswith('.'):
                    continue
                dir_path = os.path.join(dirpath, dirname)
                dir_node = FileNode(path=dir_path, is_dir=True, children=[])
                current_dir.children.append(dir_node)
            
            # 添加文件
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                file_path = os.path.join(dirpath, filename)
                language = self._detect_language(file_path)
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read()
                    except:
                        content = ""
                        
                file_node = FileNode(
                    path=file_path,
                    is_dir=False,
                    children=None,
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
    
    def _analyze_dependencies(self):
        """分析项目中的依赖关系"""
        # 这里需要根据不同语言实现不同的依赖分析逻辑
        # 简单实现：基于导入语句分析
        self.dependency_map = {}
        
        def analyze_file(file_node: FileNode):
            if not file_node.is_dir and file_node.content:
                if file_node.language == 'Python':
                    self._analyze_python_dependencies(file_node)
                elif file_node.language in ['JavaScript', 'TypeScript', 'React']:
                    self._analyze_js_dependencies(file_node)
                # 可以添加更多语言的分析逻辑
        
        def traverse(node: FileNode):
            if node.is_dir and node.children:
                for child in node.children:
                    traverse(child)
            else:
                analyze_file(node)
        
        traverse(self.file_tree)
    
    def _analyze_python_dependencies(self, file_node: FileNode):
        """分析Python文件的依赖"""
        import_lines = []
        # 使用正则表达式匹配import和from语句
        import_pattern = re.compile(r'^import\s+([a-zA-Z0-9_.,\s]+)')
        from_pattern = re.compile(r'^from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_.,\s*]+)')
        
        for line in file_node.content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append(line)
        
        self.dependency_map[file_node.path] = import_lines
    
    def _analyze_js_dependencies(self, file_node: FileNode):
        """分析JavaScript/TypeScript文件的依赖"""
        import_lines = []
        # 使用正则表达式匹配import和require语句
        import_pattern = re.compile(r'^import\s+.*\s+from\s+[\'"]([^\'"]*)[\'"]\s*;?$')
        require_pattern = re.compile(r'(?:const|let|var)\s+.*\s*=\s*require\([\'"]([^\'"]*)[\'"]\)')
        
        for line in file_node.content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or 'require(' in line:
                import_lines.append(line)
        
        self.dependency_map[file_node.path] = import_lines


if __name__ == "__main__":
    # 创建GitHub分析器实例
    github = GitHub()
    
    # 加载一个示例仓库
    repo_url = "git@github.com:ahmedkhaleel2004/gitdiagram.git"
    success = github.load_repo_from_url(repo_url)
    
    if success:
        # 获取仓库信息
        repo_info = github.get_repo_info()
        print(f"成功加载仓库: {repo_info['full_name']}")
        print(f"描述: {repo_info['description']}")
        print(f"星数: {repo_info['stars']}")
        print(f"主要语言: {repo_info['language']}")
        
        # 获取文件树，限制深度为2层
        file_tree = github.get_file_tree(max_depth=2)
        print("\n文件树结构示例 (深度限制为2层):")
        
        # 打印文件树
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
        
        # 显示项目内部依赖关系
        print("\n项目内部依赖关系示例:")
        dependencies = github.get_all_dependencies()
        for i, (file_path, deps) in enumerate(list(dependencies.items())[:3]):  # 只显示前3个文件的依赖
            rel_path = os.path.relpath(file_path, github.root_dir)
            print(f"\n{rel_path} 项目内部依赖:")
            for j, dep in enumerate(deps[:5]):  # 只显示前5个依赖
                print(f"  - {dep}")
            if len(deps) > 5:
                print(f"  - ... 等 {len(deps)-5} 个依赖")
            
            if i >= 2:  # 只显示前3个文件
                remaining = len(dependencies) - 3
                if remaining > 0:
                    print(f"\n... 等 {remaining} 个文件的依赖")
                break
                
        # 显示第三方依赖关系
        print("\n第三方依赖关系示例:")
        third_party_deps = github.get_all_third_party_dependencies()
        for i, (file_path, deps) in enumerate(list(third_party_deps.items())[:3]):  # 只显示前3个文件的依赖
            rel_path = os.path.relpath(file_path, github.root_dir)
            print(f"\n{rel_path} 第三方依赖:")
            for j, dep in enumerate(deps[:5]):  # 只显示前5个依赖
                print(f"  - {dep}")
            if len(deps) > 5:
                print(f"  - ... 等 {len(deps)-5} 个依赖")
            
            if i >= 2:  # 只显示前3个文件
                remaining = len(third_party_deps) - 3
                if remaining > 0:
                    print(f"\n... 等 {remaining} 个文件的依赖")
                break
    else:
        print("仓库加载失败，请检查URL或网络连接")
