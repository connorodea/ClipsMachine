# 🤖 Automation Guide - ClipsMachine

Complete guide to automating your clip generation and posting workflow.

---

## 🚀 Complete Automated Workflow

ClipsMachine now supports **full end-to-end automation**:

```
1. Generate clips from video
2. Create eye-catching thumbnails
3. Upload to cloud storage
4. Schedule posts at optimal times
5. Auto-post to all platforms
```

---

## 🎯 Quick Start: Fully Automated Setup

### Step 1: Generate Clips & Thumbnails
```bash
# Generate clips from YouTube video
clipsmachine clip "https://youtube.com/watch?v=VIDEO_ID"

# Generate thumbnails for all clips
clipsmachine thumbnails VIDEO_ID
```

### Step 2: Upload to Cloud Storage (Optional but Recommended)
```bash
# Upload to AWS S3
clipsmachine cloud-upload VIDEO_ID --provider s3

# Or upload to Cloudinary
clipsmachine cloud-upload VIDEO_ID --provider cloudinary
```

### Step 3: Schedule Automated Posting
```bash
# Schedule posts every 12 hours to all platforms
clipsmachine schedule VIDEO_ID --interval 12

# Or specify platforms and start time
clipsmachine schedule VIDEO_ID \
  --platforms youtube,instagram,tiktok \
  --start-time "2024-12-25T09:00:00" \
  --interval 8
```

### Step 4: Set Up Cron for Auto-Posting
```bash
# Make scheduler executable
chmod +x run_scheduler.sh

# Edit crontab
crontab -e

# Add this line to run every hour:
0 * * * * /path/to/clipsmachine/run_scheduler.sh
```

**Done!** Your clips will now auto-post on schedule 🎉

---

## 📋 Detailed Features

### 1. 🖼️ Thumbnail Generation

Generate professional thumbnails with text overlays and logos.

**Basic Usage:**
```bash
clipsmachine thumbnails VIDEO_ID
```

**With Logo Watermark:**
```bash
clipsmachine thumbnails VIDEO_ID --logo path/to/logo.png
```

**Custom Frame Timestamp:**
```bash
# Extract frame at 5 seconds into clip
clipsmachine thumbnails VIDEO_ID --timestamp 5.0
```

**What It Does:**
- Extracts best frame from each clip
- Adds title text overlay with outline
- Optional logo watermark
- Enhances brightness and saturation
- Saves to `clips_output/VIDEO_ID/thumbnails/`

**Output:**
```
clips_output/VIDEO_ID/
├── clips/
├── thumbnails/        ← Generated thumbnails
│   ├── thumbnail_01.jpg
│   ├── thumbnail_02.jpg
│   └── ...
└── manifest.json
```

---

### 2. ☁️ Cloud Storage Upload

Upload clips to cloud storage for Instagram/TikTok (they require public URLs).

#### AWS S3 Setup

**1. Create S3 config file:** `s3_config.json`
```json
{
  "aws_access_key_id": "YOUR_AWS_KEY",
  "aws_secret_access_key": "YOUR_AWS_SECRET",
  "bucket_name": "your-bucket-name",
  "region": "us-east-1"
}
```

**2. Install boto3:**
```bash
pip install boto3
```

**3. Upload clips:**
```bash
clipsmachine cloud-upload VIDEO_ID --provider s3
```

#### Cloudinary Setup

**1. Create Cloudinary config:** `cloudinary_config.json`
```json
{
  "cloud_name": "your-cloud-name",
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET"
}
```

**2. Install cloudinary:**
```bash
pip install cloudinary
```

**3. Upload clips:**
```bash
clipsmachine cloud-upload VIDEO_ID --provider cloudinary
```

**Benefits:**
- Makes Instagram/TikTok posting work (they need public URLs)
- Faster posting (already uploaded)
- CDN delivery (faster loading)
- Automatic cleanup available

**Upload Specific Clips:**
```bash
clipsmachine cloud-upload VIDEO_ID --start-index 3 --max-clips 5
```

---

### 3. ⏰ Scheduled Posting

Schedule clips to post automatically at optimal times.

#### Create Schedule

**Schedule All Clips:**
```bash
# Start 1 hour from now, post every 12 hours
clipsmachine schedule VIDEO_ID
```

**Custom Schedule:**
```bash
# Specific start time and interval
clipsmachine schedule VIDEO_ID \
  --start-time "2024-12-25T09:00:00" \
  --interval 8 \
  --platforms youtube,tiktok
```

**What Happens:**
- Creates database of scheduled posts
- Each clip gets a specific posting time
- Posts are staggered by interval (e.g., every 12 hours)
- Can post to multiple platforms simultaneously

#### View Schedule

**List Upcoming Posts:**
```bash
clipsmachine schedule-list
```

**Output:**
```
[Schedule] Upcoming posts (5):

  #1: Clip 1 → youtube,instagram
    Scheduled: 2024-12-25T09:00:00
    Title: How to Build a Successful Startup

  #2: Clip 2 → youtube,instagram
    Scheduled: 2024-12-25T21:00:00
    Title: The Secret to Productivity

  ...
```

**Show Statistics:**
```bash
clipsmachine schedule-stats
```

Output:
```
[Schedule] Statistics:
  pending: 15
  posted: 42
  failed: 3
```

#### Manual Run (Testing)

**Process Posts Now:**
```bash
clipsmachine schedule-run
```

**Dry Run (Don't Actually Post):**
```bash
clipsmachine schedule-run --dry-run
```

---

### 4. 🔄 Automated Posting with Cron

Set up truly hands-off automation with cron.

#### Option A: Use Provided Script

**1. Edit `run_scheduler.sh`:**
```bash
# Add your API keys if not in environment
export OPENAI_API_KEY="your-key"
export AWS_ACCESS_KEY_ID="your-key"  # If using S3
```

**2. Make executable:**
```bash
chmod +x run_scheduler.sh
```

**3. Add to crontab:**
```bash
crontab -e
```

Add one of these lines:

```bash
# Run every hour
0 * * * * /path/to/clipsmachine/run_scheduler.sh

# Run every 15 minutes (more frequent checking)
*/15 * * * * /path/to/clipsmachine/run_scheduler.sh

# Run twice daily at 9 AM and 9 PM
0 9,21 * * * /path/to/clipsmachine/run_scheduler.sh
```

#### Option B: Direct Command

```bash
# Run clipsmachine schedule-run every hour
0 * * * * cd /path/to/clipsmachine && source .venv/bin/activate && clipsmachine schedule-run >> scheduler.log 2>&1
```

#### Logs

Check what happened:
```bash
tail -f scheduler.log
```

---

## 🎯 Complete Workflow Examples

### Example 1: YouTube Shorts Automation

```bash
# 1. Generate clips
clipsmachine clip "https://youtube.com/watch?v=VIDEO_ID"

# 2. Generate thumbnails
clipsmachine thumbnails VIDEO_ID

# 3. Schedule for YouTube Shorts
clipsmachine schedule VIDEO_ID \
  --platforms youtube \
  --start-time "2024-12-25T08:00:00" \
  --interval 24

# 4. Set up cron (one-time)
crontab -e
# Add: 0 * * * * /path/to/run_scheduler.sh
```

Now YouTube Shorts post automatically every 24 hours starting Dec 25 at 8 AM!

### Example 2: Multi-Platform with Cloud Storage

```bash
# 1. Generate clips
clipsmachine clip "https://youtube.com/watch?v=VIDEO_ID"

# 2. Generate thumbnails
clipsmachine thumbnails VIDEO_ID --logo my_logo.png

# 3. Upload to S3 (for Instagram/TikTok)
clipsmachine cloud-upload VIDEO_ID --provider s3

# 4. Schedule to all platforms
clipsmachine schedule VIDEO_ID \
  --platforms youtube,instagram,tiktok \
  --start-time "2024-12-25T12:00:00" \
  --interval 12

# 5. Cron is already set up (from Example 1)
```

Clips now post to YouTube, Instagram, and TikTok every 12 hours!

### Example 3: Batch Processing Multiple Videos

```bash
# Process multiple videos
for url in \
  "https://youtube.com/watch?v=VIDEO1" \
  "https://youtube.com/watch?v=VIDEO2" \
  "https://youtube.com/watch?v=VIDEO3"
do
  # Generate clips
  clipsmachine clip "$url"

  # Get video ID
  video_id=$(echo "$url" | sed 's/.*v=//')

  # Generate thumbnails
  clipsmachine thumbnails "$video_id"

  # Schedule
  clipsmachine schedule "$video_id" --interval 6
done
```

### Example 4: Weekly Content Calendar

```bash
# Monday: Tech tips video
clipsmachine clip "https://youtube.com/watch?v=TECH_VIDEO"
clipsmachine schedule TECH_VIDEO \
  --start-time "2024-12-23T09:00:00" \
  --interval 24

# Wednesday: Business advice
clipsmachine clip "https://youtube.com/watch?v=BUSINESS_VIDEO"
clipsmachine schedule BUSINESS_VIDEO \
  --start-time "2024-12-25T09:00:00" \
  --interval 24

# Friday: Motivation
clipsmachine clip "https://youtube.com/watch?v=MOTIVATION_VIDEO"
clipsmachine schedule MOTIVATION_VIDEO \
  --start-time "2024-12-27T09:00:00" \
  --interval 24
```

---

## ⚙️ Advanced Configuration

### Optimal Posting Times

Research shows best times to post on each platform:

**YouTube Shorts:**
- Weekdays: 2-4 PM, 8-11 PM
- Weekends: 9-11 AM, 6-9 PM

**Instagram Reels:**
- Weekdays: 11 AM-1 PM, 7-9 PM
- Weekends: 9 AM-11 AM, 5-7 PM

**TikTok:**
- Weekdays: 6-10 AM, 7-11 PM
- Weekends: 9 AM-12 PM, 5-9 PM

**Example Schedule for Optimal Times:**
```bash
# Post at 9 AM, 2 PM, and 7 PM daily
clipsmachine schedule VIDEO_ID \
  --start-time "2024-12-25T09:00:00" \
  --interval 5

# This creates: 9 AM, 2 PM (9+5), 7 PM (2+5), 12 AM (7+5), 5 AM (12+5), ...
```

### Platform-Specific Schedules

```bash
# YouTube Shorts: Once daily at 2 PM
clipsmachine schedule VIDEO_ID \
  --platforms youtube \
  --start-time "2024-12-25T14:00:00" \
  --interval 24

# Instagram: Twice daily at 11 AM and 7 PM
clipsmachine schedule VIDEO_ID \
  --platforms instagram \
  --start-time "2024-12-25T11:00:00" \
  --interval 8

# TikTok: Three times daily
clipsmachine schedule VIDEO_ID \
  --platforms tiktok \
  --start-time "2024-12-25T09:00:00" \
  --interval 5
```

---

## 🔧 Troubleshooting

### Scheduled Posts Not Running

**Check cron is running:**
```bash
# View cron logs
grep CRON /var/log/syslog  # Linux
log show --predicate 'process == "cron"' --last 1h  # macOS
```

**Test manually:**
```bash
./run_scheduler.sh
# Check output
```

**Common Issues:**
- Cron PATH doesn't include clipsmachine → Use full path in script
- Virtual environment not activated → Script activates it automatically
- API keys not in environment → Add to run_scheduler.sh

### Cloud Upload Failing

**AWS S3:**
- Check credentials in `s3_config.json`
- Verify bucket exists and is accessible
- Check bucket permissions (public-read for uploads)

**Cloudinary:**
- Verify credentials in `cloudinary_config.json`
- Check upload quota hasn't been exceeded
- Ensure video upload is enabled in plan

### Posts Marked as Failed

**Check reasons:**
```bash
# View schedule database
sqlite3 clipsmachine_scheduler.db
SELECT * FROM scheduled_posts WHERE status='failed';
```

**Common Failures:**
- Platform API authentication failed
- Video file not found
- Rate limit exceeded
- Invalid metadata (title too long, etc.)

---

## 📊 Monitoring and Analytics

### Check Schedule Status
```bash
# Quick stats
clipsmachine schedule-stats

# Upcoming posts
clipsmachine schedule-list --limit 50

# View database directly
sqlite3 clipsmachine_scheduler.db "SELECT * FROM scheduled_posts ORDER BY scheduled_time DESC LIMIT 10;"
```

### View Logs
```bash
# Scheduler logs
tail -f scheduler.log

# Watch in real-time
watch -n 60 'clipsmachine schedule-stats'
```

---

## 🎯 Best Practices

1. **Generate Clips in Advance**
   - Process videos at night
   - Schedule posts for the week
   - Review clips before first scheduled post

2. **Use Cloud Storage for Instagram/TikTok**
   - Required for these platforms
   - Faster posting
   - Better reliability

3. **Stagger Posts Across Platforms**
   - Don't post to all platforms simultaneously
   - Different times for different platforms
   - Maximize reach

4. **Monitor First Week**
   - Check scheduler logs daily
   - Verify posts are going live
   - Adjust timing based on engagement

5. **Backup Schedule Database**
   ```bash
   cp clipsmachine_scheduler.db clipsmachine_scheduler.db.backup
   ```

---

## 🚀 Next-Level Automation

### Integration with Channel Monitoring

Watch for new uploads and auto-process:

```bash
# Python script to watch channel
# (Add to crontab to run daily)

python3 << 'EOF'
import feedparser

# RSS feed of YouTube channel
feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID"
feed = feedparser.parse(feed_url)

# Process latest video if not already processed
latest_video = feed.entries[0]
video_id = latest_video.yt_videoid

# Check if already processed...
# If not, run: clipsmachine clip + thumbnails + schedule
EOF
```

### Analytics Integration

Track performance and optimize:

```bash
# Export scheduled posts for analysis
sqlite3 clipsmachine_scheduler.db -csv \
  "SELECT * FROM scheduled_posts WHERE status='posted'" \
  > posted_clips.csv
```

---

**Happy Automating! 🤖**
