# BugBridge

Canny.io API integration and testing for bugbridge.canny.io

## Overview

This repository contains tools and documentation for working with the Canny.io API for the BugBridge feedback platform.

## Files

- **`CANNY_API_REFERENCE.md`** - Complete API reference with all endpoints, examples, and documentation
- **`POSITIONING.md`** - Platform positioning, value proposition, and market strategy
- **`JIRA_INTEGRATION_GUIDE.md`** - Guide for Jira integration (MCP server vs direct API calls)

## API Configuration

- **Subdomain:** bugbridge.canny.io
- **API Key:** Stored in `.env` file (see `.env` for configuration)
- **Documentation:** https://developers.canny.io/api-reference#intro

> **Note:** API credentials are stored in the `.env` file. Make sure to load environment variables before making API calls.

## Quick Start

1. Configure your API credentials in the `.env` file
2. See `CANNY_API_REFERENCE.md` for complete API documentation and examples
3. Review `POSITIONING.md` for platform strategy and positioning

## Status

### Canny.io API Integration ✅
✅ All CRUD operations verified and working correctly:
- **READ operations:** boards, users, posts, categories, tags, comments, votes
- **CREATE operations:** users, tags, posts
- **UPDATE operations:** users, posts ✅
- **DELETE operations:** users, posts ✅
- **STATUS operations:** Mark posts as fixed (complete) ✅

**Important Notes:**
- For post UPDATE and DELETE operations, use `postID` parameter (not `id`)
- To mark a post as fixed, change its status to `"complete"`

### Jira MCP Server Integration ✅
✅ All CRUD operations tested and working:
- **CREATE:** Create issues ✅
- **READ:** Get projects, get issues, get transitions ✅
- **UPDATE:** Update issues, add comments ✅
- **STATUS:** Transition issues (status changes) ✅

**MCP Server:** Configured in `mcp-atlassian/` directory with credentials in `.env.jira`

---

## Documentation

- `CANNY_API_REFERENCE.md` - Complete Canny.io API documentation
- `POSITIONING.md` - Platform positioning and strategy

