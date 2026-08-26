# Testing Webhooks with Postman

## The Problem

When testing webhook signature verification in Postman, you might get "Invalid webhook signature" errors even though the signature is correct. This happens because:

1. **Postman's JSON editor formats the JSON** with whitespace and specific key ordering
2. The signature is generated from a **compact JSON string** (no whitespace, sorted keys)
3. The webhook endpoint verifies against the **raw body Postman sends**
4. These strings don't match, so signature verification fails

## The Solution: Use Raw Body in Postman

### Step 1: Generate the Signature

First, run the generator script to get both the payload string and signature:

```bash
python generate_key.py
```

This outputs something like:
```
Payload (String - used for signature):
{"data":{"object":{"amount":5000,"currency":"usd","customer_email":"customer@example.com","id":"pi_1234567890","payment_method":"card"}},"id":"evt_payment_1234567890","type":"payment_intent.succeeded"}

Signature (HMAC-SHA256):
a1b2c3d4e5f6...
```

### Step 2: Configure Postman Request

1. **Method**: POST
2. **URL**: `http://localhost:8000/api/v1/webhooks`
3. **Headers**:
   - `Content-Type: application/json`
   - `X-Webhook-Signature: <paste the signature here>`
4. **Body**:
   - Select **"raw"** (NOT JSON from the dropdown)
   - Select **"Text"** from the format dropdown (NOT JSON)
   - **Copy the exact payload string** from the generator output
   - Paste it into the body field **without any modifications**

### Step 3: Send Request

Click "Send" - it should now work!

## Example Postman Configuration

**URL**: `http://localhost:8000/api/v1/webhooks`

**Headers**:
```
Content-Type: application/json
X-Webhook-Signature: e8d1f9c2a4b6d8e0f2c4a6b8d0e2f4a6c8e0f2d4b6a8c0e2d4f6a8b0c2e4d6f8
```

**Body** (raw text - copy EXACTLY from generator):
```
{"data":{"object":{"amount":5000,"currency":"usd","customer_email":"customer@example.com","id":"pi_1234567890","payment_method":"card"}},"id":"evt_payment_1234567890","type":"payment_intent.succeeded"}
```

## Important Notes

1. ✅ **DO**: Copy the exact string from `generate_key.py` output
2. ✅ **DO**: Use "raw" body type and "Text" format in Postman
3. ❌ **DON'T**: Use Postman's JSON editor (it reformats the JSON)
4. ❌ **DON'T**: Add any whitespace, newlines, or formatting
5. ❌ **DON'T**: Manually type the JSON - copy/paste only

## Alternative: Disable Signature Verification for Testing

If you want to test without signatures during development:

1. Comment out signature verification in `src/api/v1/endpoints/webhook.py`
2. Or set an environment variable to disable it
3. **Remember to re-enable for production!**

## Why Does curl Work But Postman Doesn't?

The `generate_key.py` script outputs a curl command that uses `-d` flag with the exact payload string:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: abc123..." \
  -d '{"data":...}'
```

curl sends this **exactly as-is**, so the signature matches. Postman's JSON editor reformats it, breaking the signature.
