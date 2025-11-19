# 🚀 Multi-Platform Posting Guide

ClipsMachine now supports automatic posting to **6 major social media platforms**:

- 📺 **YouTube Shorts**
- 📸 **Instagram Reels**
- 🎵 **TikTok**
- 🐦 **Twitter/X**
- 💼 **LinkedIn**
- 📘 **Facebook Reels**

---

## 🎯 Quick Start

### List Available Platforms

```bash
clipsmachine platforms
```

This shows all supported platforms, their specs, and authentication status.

### Post to Multiple Platforms

```bash
# Post to all platforms
clipsmachine post <video_id>

# Post to specific platforms
clipsmachine post <video_id> --platforms youtube,instagram,tiktok

# Post first 5 clips only
clipsmachine post <video_id> --platforms youtube --max-clips 5
```

---

## 📋 Platform Requirements

### YouTube Shorts ✅ (Ready to Use)

**Requirements:**
- Google Cloud OAuth 2.0 credentials
- File: `client_secret.json` (already set up if you use existing YouTube upload)

**Specs:**
- Max duration: 60 seconds
- Aspect ratio: 9:16 (vertical)
- Max file size: 256 MB

**Setup:**
1. Already configured if using existing YouTube upload feature
2. Run `clipsmachine post <video_id> --platforms youtube`
3. Authenticate on first use (browser will open)

---

### Instagram Reels 📸

**Requirements:**
- Instagram Business/Creator account
- Facebook Developer App
- Instagram Graph API access token

**Specs:**
- Max duration: 90 seconds
- Aspect ratio: 9:16 (vertical)
- Max file size: 100 MB

**Setup:**

1. Create Facebook App: https://developers.facebook.com/apps/
2. Add Instagram Graph API product
3. Get access token and Instagram Business Account ID
4. Create `instagram_config.json`:
   ```json
   {
     "access_token": "YOUR_INSTAGRAM_ACCESS_TOKEN",
     "instagram_account_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
   }
   ```

**Note:** Instagram API requires videos to be hosted on a public URL. Current implementation requires additional setup for video hosting (AWS S3, Cloudinary, etc.).

**Documentation:**
- https://developers.facebook.com/docs/instagram-api/getting-started
- https://developers.facebook.com/docs/instagram-api/reference/ig-user/media

---

### TikTok 🎵

**Requirements:**
- TikTok Developer account (requires approval)
- TikTok Content Posting API access
- OAuth 2.0 authentication

**Specs:**
- Max duration: 10 minutes
- Aspect ratio: 9:16 (vertical preferred)
- Max file size: 500 MB

**Setup:**

1. Apply for TikTok developer account: https://developers.tiktok.com/
2. Request Content Posting API access (requires approval)
3. Get OAuth access token
4. Create `tiktok_config.json`:
   ```json
   {
     "access_token": "YOUR_TIKTOK_ACCESS_TOKEN",
     "client_key": "YOUR_CLIENT_KEY",
     "client_secret": "YOUR_CLIENT_SECRET"
   }
   ```

**Note:** TikTok API access requires developer account approval and user OAuth consent.

**Documentation:**
- https://developers.tiktok.com/doc/content-posting-api-get-started/

---

### Twitter/X 🐦

**Requirements:**
- Twitter Developer account
- Twitter API v2 access
- Bearer token or OAuth credentials

**Specs:**
- Max duration: 140 seconds (2:20)
- Aspect ratio: 16:9 (landscape preferred)
- Max file size: 512 MB

**Setup:**

1. Create Twitter Developer App: https://developer.twitter.com/
2. Get API credentials
3. Create `twitter_config.json`:
   ```json
   {
     "bearer_token": "YOUR_BEARER_TOKEN",
     "api_key": "YOUR_API_KEY",
     "api_secret": "YOUR_API_SECRET",
     "access_token": "YOUR_ACCESS_TOKEN",
     "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
   }
   ```

**Recommended:** Install `tweepy` library for full Twitter API support:
```bash
pip install tweepy
```

**Documentation:**
- https://developer.twitter.com/en/docs/twitter-api

---

### LinkedIn 💼

**Requirements:**
- LinkedIn Page (Company/Organization page)
- LinkedIn Developer App
- OAuth 2.0 access token

**Specs:**
- Max duration: 10 minutes
- Aspect ratio: 16:9 (landscape)
- Max file size: 200 MB
- Min duration: 3 seconds

**Setup:**

1. Create LinkedIn App: https://www.linkedin.com/developers/
2. Request Video API access
3. Get OAuth access token
4. Create `linkedin_config.json`:
   ```json
   {
     "access_token": "YOUR_LINKEDIN_ACCESS_TOKEN",
     "organization_id": "YOUR_LINKEDIN_PAGE_ID"
   }
   ```

**Documentation:**
- https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api

---

### Facebook Reels 📘

**Requirements:**
- Facebook Page
- Facebook Developer App
- Graph API access token

**Specs:**
- Max duration: 90 seconds
- Aspect ratio: 9:16 (vertical)
- Max file size: 1 GB
- Min duration: 3 seconds

**Setup:**

1. Create Facebook App: https://developers.facebook.com/apps/
2. Add Pages API and Video API
3. Get Page access token
4. Create `facebook_config.json`:
   ```json
   {
     "access_token": "YOUR_PAGE_ACCESS_TOKEN",
     "page_id": "YOUR_FACEBOOK_PAGE_ID"
   }
   ```

**Note:** Similar to Instagram, requires video to be hosted on public URL.

**Documentation:**
- https://developers.facebook.com/docs/video-api/

---

## 💡 Usage Examples

### Example 1: Post to YouTube Shorts Only

```bash
# Process video and generate clips
clipsmachine clip "https://youtube.com/watch?v=VIDEO_ID"

# Post to YouTube Shorts
clipsmachine post VIDEO_ID --platforms youtube
```

### Example 2: Post to Multiple Platforms

```bash
# Post to YouTube, Instagram, and TikTok
clipsmachine post VIDEO_ID --platforms youtube,instagram,tiktok
```

### Example 3: Post Specific Clips

```bash
# Post clips 3-7 only
clipsmachine post VIDEO_ID --platforms youtube --start-index 3 --max-clips 5
```

### Example 4: Sequential Upload

```bash
# Upload to platforms one at a time (instead of parallel)
clipsmachine post VIDEO_ID --platforms youtube,tiktok --sequential
```

---

## 🔧 Advanced Configuration

### Parallel vs Sequential Uploads

**Parallel (Default):**
- Uploads to all platforms simultaneously
- Faster but uses more resources
- Recommended for most use cases

```bash
clipsmachine post VIDEO_ID --platforms youtube,instagram,tiktok
```

**Sequential:**
- Uploads to one platform at a time
- Slower but more stable
- Use if experiencing rate limit issues

```bash
clipsmachine post VIDEO_ID --platforms youtube,instagram,tiktok --sequential
```

### Privacy Settings

```bash
# YouTube: Set privacy to unlisted or private
clipsmachine post VIDEO_ID --platforms youtube --privacy unlisted

# Options: public, unlisted, private
```

---

## 📊 Platform Comparison

| Platform | Max Duration | Aspect Ratio | Max Size | Auth Required | API Difficulty |
|----------|--------------|--------------|----------|---------------|----------------|
| YouTube Shorts | 60s | 9:16 | 256 MB | ✅ Yes | ⭐ Easy |
| Instagram Reels | 90s | 9:16 | 100 MB | ✅ Yes | ⭐⭐⭐ Hard |
| TikTok | 10min | 9:16 | 500 MB | ✅ Yes | ⭐⭐⭐ Hard |
| Twitter/X | 140s | 16:9 | 512 MB | ✅ Yes | ⭐⭐ Medium |
| LinkedIn | 10min | 16:9 | 200 MB | ✅ Yes | ⭐⭐ Medium |
| Facebook Reels | 90s | 9:16 | 1 GB | ✅ Yes | ⭐⭐⭐ Hard |

---

## 🎯 Recommended Aspect Ratios

ClipsMachine generates videos in 9:16 aspect ratio by default, which is optimal for:
- ✅ YouTube Shorts
- ✅ Instagram Reels
- ✅ TikTok
- ✅ Facebook Reels

For Twitter and LinkedIn (which prefer 16:9), you can generate clips in landscape:

```bash
clipsmachine clip "URL" --aspect-ratio 16:9
```

---

## 🚧 Current Limitations

### Instagram & Facebook
- Require video to be hosted on public URL (not local file)
- Implementation requires additional video hosting setup
- Consider using AWS S3, Cloudinary, or similar service

### TikTok
- Requires approved developer account
- Content Posting API access needs application
- OAuth flow requires user consent

### Twitter
- Video API has rate limits
- Recommended to install `tweepy` library for full support

### All Platforms
- Each platform has different API quotas and rate limits
- Some platforms require business/creator accounts
- API access may require approval process

---

## 🔮 Future Enhancements

- [ ] Automatic video hosting for Instagram/Facebook
- [ ] Thumbnail generation for each platform
- [ ] Platform-specific caption optimization
- [ ] Scheduled posting (post queue system)
- [ ] Analytics integration
- [ ] A/B testing for titles/thumbnails
- [ ] Batch processing multiple videos

---

## 🆘 Troubleshooting

### "Authentication failed"
1. Check config file exists and has correct format
2. Verify access tokens are valid (not expired)
3. Ensure API permissions are granted

### "Rate limit exceeded"
1. Use `--sequential` flag to slow down uploads
2. Check platform-specific quotas
3. Wait before retrying

### "Video validation failed"
1. Check video meets platform specs (duration, size, format)
2. Ensure aspect ratio matches platform requirements
3. Verify video file is not corrupted

### "Platform not initialized"
1. Check platform name is correct (lowercase)
2. Run `clipsmachine platforms` to see available platforms
3. Ensure config file is in correct location

---

## 📚 Additional Resources

- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)
- [TikTok Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started/)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)
- [LinkedIn Video API](https://learn.microsoft.com/en-us/linkedin/)
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api)

---

## 🤝 Contributing

Want to add support for more platforms? Contributions welcome!

1. Implement platform class inheriting from `Platform` base class
2. Add to `platforms/__init__.py` registry
3. Update this documentation
4. Submit pull request

---

**Happy posting! 🚀**
