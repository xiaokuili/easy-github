# EasyGithub

> 将任何GitHub项目进行分层可视化展示

## 核心功能
- 📊 **模块间依赖关系可视化** - 清晰展示项目各模块之间的依赖结构
- 🔍 **模块内结构可视化** - 深入分析单个模块的内部组织结构

## 技术栈

### 前端
- **框架**: Next.js, TypeScript
- **样式**: Tailwind CSS, ShadCN UI

### 后端
- **服务**: Langgraph
- **数据库**: PostgreSQL (with Drizzle ORM)

### 智能分析
- **AI引擎**: Deepseek

### 部署与运维
- **部署**: Vercel (前端), EC2 (后端)
- **CI/CD**: GitHub Actions
- **数据分析**: PostHog, Api-Analytics


# Thanks 
[gitdiagram](https://github.com/ahmedkhaleel2004/gitdiagram/blob/6af338ff46169ea2f1397e34359abca222afd39c/backend/app/prompts.py#L8
)
```
# imagine it like this:
# def prompt1(file_tree, readme) -> explanation of diagram
# def prompt2(explanation, file_tree) -> maps relevant directories and files to parts of diagram for interactivity
# def prompt3(explanation, map) -> Mermaid.js code
```