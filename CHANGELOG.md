# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.3] - 2026-04-26

### Added

#### Capture/Summarize Bug Fix (沉淀功能修复)

##### Frontend: HTTP 422 & Toast Loop
- Fixed `POST /api/threads/{id}/summarize` request missing `Content-Type: application/json` header and request body
- Added `body: JSON.stringify({ max_messages: 50 })` to match FastAPI Pydantic validation
- Improved error handling: non-Error objects now serialized via `JSON.stringify()` instead of showing hardcoded text
- Prevented toast error infinite loop caused by effect re-triggering on failed state

##### Backend: Empty Message Text in Summarization
- Fixed `summarize_thread` reading raw msgpack checkpoint data without deserializing LangChain objects
- Added `serialize_channel_values()` call to convert msgpack `ExtType` objects to JSON-safe dicts
- Messages are now properly extracted for LLM summarization

#### Admin Knowledge Base Management (管理员知识库管理)
- Admin knowledge base list page at `/workspace/admin/knowledge`
- Edit knowledge bases (name, description, visibility) via admin interface
- Admin API endpoint: `PUT /api/admin/knowledge/{kb_id}`

#### User Knowledge Base Creation (用户知识库创建)
- User knowledge base creation now respects visibility field
- Options: Private (私有) / Workspace (工作区共享)
- Visibility is properly saved during creation

### Fixed

#### Knowledge Base Creation Bug
- Fixed KB creation ignoring "workspace knowledge" selection
- Visibility field is now properly used instead of hardcoded "private"

#### Skill Management Permissions (技能管理权限)
- Fixed: Regular users could not create custom skills
  - Changed `POST /api/skills/custom` from `require_owner_user` to `require_user`
- Fixed: Admins could not edit built-in (public) skills
  - Updated `PUT /api/skills/custom/{skill_name}` to support admin editing of public skills
  - Added proper handling for both custom and public skill files

#### HTTP 413 Upload Error
- Fixed nginx configuration for large file uploads
- Added `client_max_body_size 100M` and `proxy_request_buffering off`
- Fixed uvicorn command to remove invalid `--limit-max-bytes` parameter

## [1.4.2] - 2026-04-25

### Added

#### Feishu Platform Tools (飞书平台工具)

**Cloud Drive (云盘)**
- `feishu_drive_file_delete` - Delete cloud drive files
- `feishu_drive_file_move` - Move files within cloud drive
- `feishu_drive_file_copy` - Copy files in cloud drive

**Bitable (多维表格)**
- `feishu_bitable_record_create` - Create single record in bitable table
- `feishu_bitable_record_update` - Update single record in bitable table
- `feishu_bitable_record_delete` - Delete single record from bitable table
- `feishu_bitable_table_list` - List all tables in a bitable
- `feishu_bitable_field_list` - List all fields in a bitable table

**IM (消息增强)**
- `feishu_message_get` - Get message content by ID

**Calendar (日历)**
- `feishu_calendar_event_get` - Get calendar event by ID

**Task (任务)**
- `feishu_task_get` - Get task details by GUID

**Mail (邮件)**
- `feishu_mail_create_draft` - Create mail draft

**Sheets (电子表格)**
- `feishu_sheet_create` - Create new spreadsheet in folder

### Fixed

- `feishu_doc_write` - Fixed block_id and response parsing bugs
- `feishu_sheet_write` - Fixed request body format and response field names
- `feishu_sheet_read` / `feishu_sheet_range` - Fixed response data access

## [1.4.0] - 2026-04-20

### Added

#### Scheduled Tasks (定时任务)
- Task CRUD operations with SQLite persistence
- Trigger types: Cron expressions and Interval (minutes/hours/days)
- One-time task support
- Task execution with LangGraph integration
- Execution history with result summary (完整 AI 响应)
- Pause/Resume task controls
- Task sharing between users

#### Knowledge Base (知识库)
- RAG-based knowledge management system
- Document upload and processing
- Vector storage with embedding support
- Knowledge retrieval in agent context
- Web content extraction (jina.ai)
- Knowledge base CRUD operations

#### IM Channels Configuration (IM 渠道配置)
- 飞书 (Feishu) integration
- Slack integration with Socket Mode support
- Telegram Bot integration
- 企业微信 (WeCom) integration
- 钉钉 (DingTalk) integration (NEW)
- Channel enable/disable controls
- Channel restart functionality
- Admin UI for channel management at `/workspace/admin/models/mcp/channels`

#### Navigation Restructuring
- MCP Configuration moved to Admin Console
- IM Channels moved to Admin Console
- Consistent admin navigation structure
- User Settings dropdown cleanup

### Fixed

#### Bug Fixes
- nginx routing for `/api/tasks` and `/api/knowledge` endpoints
- nginx routing for `/api/channels` endpoint (trailing slash handling)
- TypeScript type errors in channels-admin-page.tsx
- TypeScript type errors in mcp-admin-page.tsx
- useMyCustomSkills hook missing refetch return value
- Scheduled tasks datetime.UTC alias compatibility
- Skills custom endpoint 403 permission error
- Cron expression user guidance with examples

### Changed

#### Backend
- Added `tasks` and `knowledge` to router exports
- Updated channel models with new field types
- Fixed _get_skill_shares import issues
- Enhanced task execution with result summary

#### Frontend
- Enhanced task detail page with trigger editing
- Added cron guidance i18n strings
- Fixed nullish coalescing operator usage
- Improved channel configuration UI

## [1.3.0] - 2026-04-19

### Added

#### Scheduled Tasks System
- Task creation with prompt templates
- Cron and interval trigger configuration
- Task pause/resume functionality
- Task execution via "Run Now" button
- Task sharing between users

#### Knowledge Base
- RAG knowledge management
- Document embedding and retrieval
- Web content extraction

### Changed

#### Backend
- Task router with SQLite persistence
- Knowledge router with vector storage
- Channel service improvements

## [1.2.0] - 2026-04-17

### Added

#### Skill User Isolation
- Regular users now only see skills they created or that are shared publicly by admin
- Admin (owner) can see ALL skills
- Skills without share records are treated as private
- Visibility rules: own skills, public skills, workspace-shared skills
- SkillShare records auto-created on custom skill creation and remote install

#### Token Statistics
- File-based token usage tracking per user
- Admin token usage dashboard at `/workspace/admin/token-usage`
- TokenUsageMiddleware logs token consumption with WARNING level

#### Model Presets
- 20+ pre-configured model presets for OpenAI, Anthropic, Google, Azure, Groq, DeepSeek, Ollama, etc.
- Quick model selection in configuration center
- Support for custom model endpoints

#### Configuration Center Enhancements
- MCP server configuration: type, url, headers, description fields
- Tool configuration: use, extra_params fields
- Full parameter support for MCP and tools

### Fixed

#### Preview Window Flicker
- Fixed flickering during agent execution by using CSS visibility instead of conditional rendering

#### Markdown Download
- Added download button in preview mode for markdown files
- Download button uses proper blob URL to save content with correct filename

#### Artifact Download Links
- Fixed artifact links in markdown content (Streamdown rendered) to properly trigger downloads
- Added ArtifactLinkContextProvider to pass threadId through React context
- ArtifactLink now converts internal /mnt/... paths to proper download URLs

### Changed

#### Frontend Updates
- File cards in chat messages are now clickable and trigger downloads
- Image files open in new tab for preview
- Non-image files download directly when clicked
- Download icon added to file cards for visual feedback

## [1.1.0] - 2026-04-16

### Added

#### Admin Configuration Center UI
- Complete config.yaml management through web UI at `/workspace/admin/config`
- System configuration: log_level, token_usage, checkpointer settings
- Model configuration: CRUD operations, API key management
- Sandbox configuration: provider type, bash permissions, timeouts
- Tool configuration: enable/disable tools, group management
- Upload configuration: size limits, allowed extensions, markdown conversion
- Skills configuration: paths, auto-update, security scan settings
- MCP server configuration: command, args, env variables
- Tracing configuration: LangSmith and Langfuse integration
- Configuration validation with detailed error messages
- Sensitive fields (API keys) are masked in responses
- Real-time config reload without service restart

#### User Skills Management
- **Skills Settings Page**: Available at `/workspace/settings/skills` (accessible via Settings Dialog)
- **All Skills Tab**: Browse and enable/disable all available skills
- **My Creations Tab**: View and manage custom skills created by the user
- **Shared Records Tab**: Share skills and rate other skills
- **Custom Skill Creation**: Create new skills with SKILL.md template
  - Name validation and uniqueness checking
  - Security scan before creation
  - Frontmatter validation
- **Skill Sharing**: Share skills with visibility options
  - Public: visible to all users
  - Workspace: visible to workspace members only
- **Skill Rating**: Rate skills with 1-5 stars and optional comments
- **Skill Configuration**: Personal skill settings and default skill selection

#### New Backend APIs
- `GET /api/user/skills` - List user skill configurations
- `PUT /api/user/skills/{skill_name}/config` - Update skill configuration
- `POST /api/user/skills/{skill_name}/enable` - Enable a skill
- `POST /api/user/skills/{skill_name}/disable` - Disable a skill
- `GET /api/user/skills/{skill_name}/ratings` - Get skill ratings
- `POST /api/skills/custom` - Create custom skill
- `POST /api/skills/{skill_name}/share` - Share a skill
- `POST /api/skills/{skill_name}/unshare` - Unshare a skill
- `GET /api/skills/shared` - List shared skills
- `POST /api/skills/{skill_name}/rate` - Rate a skill

#### New Frontend Components
- `UserSkillsPage` - Main skills management interface
- `CreateSkillDialog` - Skill creation with markdown editor
- `ShareSkillDialog` - Share settings with visibility options
- `RateSkillDialog` - Star rating with comment

### Fixed
- Fixed NameError in skills.py where response models were used before definition
- Fixed path configuration in admin config (was using non-existent `data_dir`)
- Fixed type errors in AdminTracingResponse (langfuse config)
- Removed unused imports causing lint warnings

### Changed
- Updated Skill type to include all fields from backend response
- Settings Dialog now includes Skills section in navigation

### Security
- Skill creation blocked if security scan detects malicious content
- API key fields are masked in GET responses
- Password strength requirements enforced for BY_ADMIN_PASSWORD

## [1.0.0] - 2026-04-13

### Added
- Initial MicX release based on DeerFlow
- Admin management console with monitoring, config, skills, users, workspaces, models
- Multi-user support with workspace collaboration
- Thread visibility model (private by default)
- Brand customization (MicX branding)
- Chinese localization complete
- Production security hardening
- SQLite checkpoint persistence

---

## Release Types

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
