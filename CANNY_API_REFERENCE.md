# Canny.io API Reference - bugbridge.canny.io

**Subdomain:** bugbridge.canny.io  
**Base URL:** `https://canny.io/api/v1`  
**Documentation:** https://developers.canny.io/api-reference#intro

> **Note:** API key and configuration values are stored in `.env` file. See Authentication & Configuration section below.

---

## Table of Contents

1. [Authentication & Configuration](#authentication--configuration)
2. [READ Operations](#read-operations)
3. [CREATE Operations](#create-operations)
4. [UPDATE Operations](#update-operations)
5. [DELETE Operations](#delete-operations)
6. [Status Management](#status-management)
7. [Quick Reference](#quick-reference)

---

## Authentication & Configuration

### API Key Storage
API key and configuration values are stored in the `.env` file:

```env
CANNY_API_KEY=your_api_key_here
CANNY_SUBDOMAIN=bugbridge.canny.io
CANNY_BOARD_ID=your_board_id
CANNY_ADMIN_USER_ID=your_admin_user_id
```

**Important:** Never commit the `.env` file to version control. It contains sensitive credentials.

### Request Format
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:** JSON with `apiKey` and endpoint-specific parameters

### Example Request Structure
```bash
curl -X POST https://canny.io/api/v1/ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    ...other parameters
  }'
```

**Note:** Replace `YOUR_API_KEY` with your actual API key from the `.env` file.

---

## READ Operations

### List Boards
**Endpoint:** `POST /api/v1/boards/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY"
}
```

**Response:**
```json
{
    "boards": [{
        "id": "691d7a43749ccd4a28189d49",
        "name": "Feedback and feature requests",
        "postCount": 1,
        "url": "https://bugbridge.canny.io/admin/board/feedback-and-feature-requests"
    }]
}
```

---

### Retrieve Board
**Endpoint:** `POST /api/v1/boards/retrieve`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "id": "691d7a43749ccd4a28189d49"
}
```

---

### List Users
**Endpoint:** `POST /api/v2/users/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "limit": 10
}
```

**Response:** Returns users array with cursor-based pagination

---

### Retrieve User
**Endpoint:** `POST /api/v1/users/retrieve`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "id": "6072c28346f94e0f03499a52"
}
```

---

### List Posts
**Endpoint:** `POST /api/v1/posts/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "limit": 10,
  "skip": 0
}
```

**Response:** Returns posts array with skip-based pagination

---

### Retrieve Post
**Endpoint:** `POST /api/v1/posts/retrieve`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "id": "691d7c0a58a681e83ef06510"
}
```

**Note:** Use `id` parameter for retrieve operations

---

### List Categories
**Endpoint:** `POST /api/v1/categories/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "boardID": "691d7a43749ccd4a28189d49"
}
```

---

### List Tags
**Endpoint:** `POST /api/v1/tags/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY"
}
```

---

### List Comments
**Endpoint:** `POST /api/v1/comments/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "limit": 10
}
```

---

### List Votes
**Endpoint:** `POST /api/v1/votes/list`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "limit": 10
}
```

---

## CREATE Operations

### Create/Update User
**Endpoint:** `POST /api/v1/users/create_or_update`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "email": "user@example.com",
  "name": "User Name",
  "userID": "external-user-id-123"
}
```

**Response:**
```json
{
    "id": "65b12e1dd9538cfb910c5f0a"
}
```

**Note:** This endpoint creates a new user or updates an existing one (matched by email)

---

### Create Post
**Endpoint:** `POST /api/v1/posts/create`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "boardID": "691d7a43749ccd4a28189d49",
  "title": "Post Title",
  "details": "Post details",
  "authorID": "6072c28346f94e0f03499a52"
}
```

**Response:**
```json
{
    "id": "691e65c88b7272a3b06e0a19"
}
```

---

### Create Tag
**Endpoint:** `POST /api/v1/tags/create`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "name": "Tag Name",
  "boardID": "691d7a43749ccd4a28189d49"
}
```

**Response:** Returns created tag object

---

## UPDATE Operations

### Update User
**Endpoint:** `POST /api/v1/users/create_or_update`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "email": "user@example.com",
  "name": "Updated Name"
}
```

**Response:**
```json
{
    "id": "65b12e1dd9538cfb910c5f0a"
}
```

---

### Update Post
**Endpoint:** `POST /api/v1/posts/update`

⚠️ **Important:** Use `postID` parameter, NOT `id`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "postID": "691d7c0a58a681e83ef06510",
  "title": "Updated Title",
  "details": "Updated details",
  "eta": "12/2025",
  "etaPublic": true,
  "customFields": {},
  "imageURLs": []
}
```

**Response:**
```
success
```

**Updateable Fields:**
- `title` - Post title
- `details` - Post details/description
- `eta` - Estimated time (MM/YYYY format)
- `etaPublic` - Boolean for ETA visibility
- `customFields` - Custom field values
- `imageURLs` - Array of image URLs

---

## DELETE Operations

### Delete User
**Endpoint:** `POST /api/v1/users/delete`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "id": "65b12e1dd9538cfb910c5f0a"
}
```

**Response:**
```
success
```

---

### Delete Post
**Endpoint:** `POST /api/v1/posts/delete`

⚠️ **Important:** Use `postID` parameter, NOT `id`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "postID": "691e65c88b7272a3b06e0a19"
}
```

**Response:**
```
success
```

---

## Status Management

### Change Post Status (Mark as Fixed)
**Endpoint:** `POST /api/v1/posts/change_status`

⚠️ **Important:** Use `postID` parameter, NOT `id`

**Request:**
```json
{
  "apiKey": "YOUR_API_KEY",
  "postID": "YOUR_POST_ID",
  "status": "complete",
  "changerID": "YOUR_ADMIN_USER_ID",
  "shouldNotifyVoters": true,
  "commentValue": "This issue has been fixed!"
}
```

**Response:** Returns updated post object with new status

**Available Status Values:**
- `"open"` - Default status for new posts
- `"in progress"` - Post is being worked on
- `"complete"` - Post is fixed/completed ✅ (This is the "fixed" status)

**Required Parameters:**
- `postID` - The post ID (use `postID`, not `id`)
- `status` - Status value (use `"complete"` to mark as fixed)
- `changerID` - The ID of the user/admin making the change
- `shouldNotifyVoters` - Boolean (true/false) to notify voters

**Optional Parameters:**
- `commentValue` - Optional message explaining the status change

**Example - Mark Post as Fixed:**
```bash
curl -X POST https://canny.io/api/v1/posts/change_status \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    "postID": "YOUR_POST_ID",
    "status": "complete",
    "changerID": "YOUR_ADMIN_USER_ID",
    "shouldNotifyVoters": true,
    "commentValue": "This bug has been fixed in the latest release."
  }'
```

---

## Quick Reference

### Parameter Naming Convention

| Operation | Parameter Name | Example |
|-----------|---------------|---------|
| Retrieve Post | `id` | `{"id": "691d7c0a58a681e83ef06510"}` |
| Update Post | `postID` | `{"postID": "691d7c0a58a681e83ef06510"}` |
| Delete Post | `postID` | `{"postID": "691d7c0a58a681e83ef06510"}` |
| Change Post Status | `postID` | `{"postID": "691d7c0a58a681e83ef06510"}` |

⚠️ **Common Mistake:** Using `id` instead of `postID` for update/delete/status operations will result in `{"error": "invalid postID"}`

---

### Account Information

- **Subdomain:** bugbridge.canny.io
- **Boards:** 1 board ("Feedback and feature requests")
- **Board ID:** See `.env` file for `CANNY_BOARD_ID`
- **Admin User ID:** See `.env` file for `CANNY_ADMIN_USER_ID`

**Note:** All IDs and credentials are stored in the `.env` file for security.

---

### Status Summary

✅ **All CRUD operations verified and working:**
- ✅ READ: boards, users, posts, categories, tags, comments, votes
- ✅ CREATE: users, posts, tags
- ✅ UPDATE: users, posts
- ✅ DELETE: users, posts
- ✅ STATUS: Mark posts as fixed (complete)

---

## Common Use Cases

### 1. Create a Post
```bash
curl -X POST https://canny.io/api/v1/posts/create \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    "boardID": "YOUR_BOARD_ID",
    "title": "New Bug Report",
    "details": "Bug description",
    "authorID": "YOUR_AUTHOR_ID"
  }'
```

### 2. Update a Post
```bash
curl -X POST https://canny.io/api/v1/posts/update \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    "postID": "YOUR_POST_ID",
    "title": "Updated Title",
    "details": "Updated details"
  }'
```

### 3. Mark Post as Fixed
```bash
curl -X POST https://canny.io/api/v1/posts/change_status \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    "postID": "YOUR_POST_ID",
    "status": "complete",
    "changerID": "YOUR_ADMIN_USER_ID",
    "shouldNotifyVoters": true,
    "commentValue": "Fixed in version 2.0"
  }'
```

### 4. Delete a Post
```bash
curl -X POST https://canny.io/api/v1/posts/delete \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "YOUR_API_KEY",
    "postID": "YOUR_POST_ID"
  }'
```

**Note:** Replace all `YOUR_*` placeholders with actual values from your `.env` file or account.

---

**Last Updated:** November 19, 2025

