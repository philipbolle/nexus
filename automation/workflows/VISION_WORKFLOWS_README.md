# NEXUS Vision Workflows

**Created:** January 19, 2026
**Status:** Working

---

## What Was Done

Created two AI vision workflows for n8n that analyze images using Google's Gemini 2.5 Flash model:

1. **Photo Vision** (`photo_vision.json`) - General photo analysis
2. **Screenshot Helper** (`screenshot_helper.json`) - Screenshot analysis with error detection

Both workflows were imported to n8n and tested successfully.

---

## Endpoints

### Photo Vision
- **URL:** `POST http://localhost:5678/webhook/photo-vision`
- **Purpose:** Describe photos, identify objects, read text in images
- **From iPhone (Tailscale):** `http://100.94.29.101:5678/webhook/photo-vision`

### Screenshot Helper
- **URL:** `POST http://localhost:5678/webhook/screenshot-helper`
- **Purpose:** Analyze screenshots, identify apps, detect errors, suggest fixes
- **From iPhone (Tailscale):** `http://100.94.29.101:5678/webhook/screenshot-helper`

---

## How to Use

### Request Format
```json
{
  "image": "<base64-encoded-image>",
  "mime_type": "image/png",
  "prompt": "Your question about the image"
}
```

### Example - Analyze a Photo
```bash
# Encode an image to base64
IMG=$(base64 -w0 /path/to/photo.jpg)

# Send to photo-vision
curl -X POST http://localhost:5678/webhook/photo-vision \
  -H "Content-Type: application/json" \
  -d "{\"image\": \"$IMG\", \"mime_type\": \"image/jpeg\", \"prompt\": \"What do you see in this photo?\"}"
```

### Example - Get Help with Screenshot
```bash
# Encode screenshot
IMG=$(base64 -w0 ~/screenshot.png)

# Send to screenshot-helper
curl -X POST http://localhost:5678/webhook/screenshot-helper \
  -H "Content-Type: application/json" \
  -d "{\"image\": \"$IMG\", \"mime_type\": \"image/png\", \"prompt\": \"What error is shown and how do I fix it?\"}"
```

### Response Format
```json
{
  "success": true,
  "analysis": "The image shows...",
  "model": "gemini-2.5-flash",
  "finish_reason": "STOP"
}
```

---

## Quick Test

Test with a 1x1 red pixel:
```bash
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

curl -s -X POST http://localhost:5678/webhook/photo-vision \
  -H "Content-Type: application/json" \
  -d "{\"image\": \"$IMG\", \"mime_type\": \"image/png\", \"prompt\": \"What color?\"}"
```

Expected response: `{"success":true,"analysis":"The color is **red**.","model":"gemini-2.5-flash","finish_reason":"STOP"}`

---

## Setup / Re-Import

If workflows need to be re-imported:

```bash
cd ~/nexus/automation/workflows
./import_iphone_workflows.sh
```

Then restart n8n:
```bash
cd ~/nexus
docker compose restart n8n
```

---

## Files

| File | Description |
|------|-------------|
| `photo_vision.json` | Photo analysis workflow |
| `screenshot_helper.json` | Screenshot helper workflow |
| `import_iphone_workflows.sh` | One-click import script |

---

## Technical Notes

- **Model:** Gemini 2.5 Flash (free tier)
- **Why not Groq?** Groq doesn't have vision models available
- **Why not Gemini 2.0?** Quota was exhausted, 2.5 Flash works
- **API Key:** Uses `GOOGLE_AI_API_KEY` from environment
- **Timeout:** 60 seconds per request

---

## iPhone Shortcut Integration

To use from iPhone Shortcuts:

1. Use "Get Contents of URL" action
2. Set Method to POST
3. Set URL to `http://100.94.29.101:5678/webhook/photo-vision`
4. Add Header: `Content-Type: application/json`
5. Set Request Body to JSON with `image`, `mime_type`, `prompt` fields
6. Use "Base64 Encode" action on the image first
