# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
