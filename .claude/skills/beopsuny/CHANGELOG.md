# Changelog

All notable changes to the Beopsuny skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-26

### Changed
- **BREAKING**: SKILL.md restructured to role-based 6-section format
  - Reduced from 483 lines to 330 lines (30% reduction)
  - New structure: Overview, Setup, Core Workflows, Commands, Use Cases, Resources
  - Applied Korean/English hybrid naming convention
- **BREAKING**: Directory structure aligned with Agent Skills specification (Phase 1)
  - `docs/` → `references/`
  - Static data moved from `config/` → `assets/`
  - `config/` now contains only secrets (settings.yaml)

### Added
- `references/quick-reference.md` - Frequently used commands cheatsheet
- `references/external-sites.md` - External reference sites list
- Frontmatter fields: license, compatibility, metadata
- CI validation with `skills-ref validate` workflow
- `assets/` directory for static data files
  - law_index.yaml, legal_terms.yaml, clause_references.yaml, forms.yaml
  - checklists/ subdirectory

### Removed
- Duplicate sections in SKILL.md
  - "Instructions for Claude" merged into "Overview" (kept at end for recall)
  - "Quick Reference" → references/quick-reference.md
  - "외부 참고 사이트" → references/external-sites.md
- Redundant data in settings.yaml (major_laws, targets)

## [1.x.x] - Previous versions

### Added
- Initial release with Korean law research capabilities
- National Law Information Center API integration
- National Assembly bill tracking
- Legal checklists (7 types)
- Contract review support
- International expansion guide

---

## Versioning Policy

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking changes (structure, API) | Major | 1.0.0 → 2.0.0 |
| New features, capabilities | Minor | 2.0.0 → 2.1.0 |
| Bug fixes, data updates | Patch | 2.0.1 → 2.0.2 |
