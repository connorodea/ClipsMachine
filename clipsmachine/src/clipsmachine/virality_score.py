"""
Virality score prediction for video clips.

Analyzes clips to predict their potential virality based on:
- Hook strength (first 3 seconds)
- Emotional peaks and storytelling
- Pacing and engagement
- Trend alignment
"""

import os
from typing import Dict, Any
from openai import OpenAI


def calculate_virality_score(
    clip_text: str,
    clip_duration: float,
    clip_index: int,
) -> Dict[str, Any]:
    """
    Calculate a virality score (0-100) for a video clip using GPT-4.

    Analyzes:
    - Hook strength: Does it grab attention in the first 3 seconds?
    - Emotional impact: Does it evoke strong emotions?
    - Pacing: Is the content well-paced and engaging?
    - Shareability: Would viewers want to share this?
    - Trend alignment: Does it align with current content trends?

    Args:
        clip_text: The transcript text of the clip
        clip_duration: Duration of the clip in seconds
        clip_index: Index of the clip in the video

    Returns:
        Dict with:
        - virality_score: 0-100 score
        - hook_strength: 0-100 score for opening hook
        - emotional_impact: 0-100 score for emotional resonance
        - shareability: 0-100 score for share potential
        - insights: Text insights about why this score was given
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "virality_score": 50,
            "hook_strength": 50,
            "emotional_impact": 50,
            "shareability": 50,
            "insights": "OpenAI API key not set - using default scores",
        }

    client = OpenAI(api_key=api_key)

    # Construct the prompt
    prompt = f"""You are an expert in viral short-form video content analysis. Analyze this video clip transcript and predict its virality potential.

Clip duration: {clip_duration:.1f} seconds
Transcript:
{clip_text}

Provide a detailed virality analysis with scores (0-100) for:

1. **Hook Strength**: Does the opening grab attention immediately? Does it create curiosity or intrigue in the first 3 seconds?

2. **Emotional Impact**: Does the content evoke strong emotions (inspiration, humor, surprise, relatability)?

3. **Shareability**: Would viewers want to share this with others? Does it have a clear takeaway or "wow" moment?

4. **Overall Virality Score**: Based on all factors, what's the overall potential for this clip to go viral on platforms like YouTube Shorts, TikTok, Instagram Reels?

Format your response as JSON:
{{
  "virality_score": <0-100>,
  "hook_strength": <0-100>,
  "emotional_impact": <0-100>,
  "shareability": <0-100>,
  "insights": "<2-3 sentence explanation of the scores and what makes this clip strong or weak>"
}}

Be critical but fair. Most clips should score 40-70. Only truly exceptional clips should score above 80.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a viral content analyst specializing in short-form video. Provide honest, data-driven assessments.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        import json

        result = json.loads(response.choices[0].message.content)

        # Ensure all required fields are present with defaults
        return {
            "virality_score": result.get("virality_score", 50),
            "hook_strength": result.get("hook_strength", 50),
            "emotional_impact": result.get("emotional_impact", 50),
            "shareability": result.get("shareability", 50),
            "insights": result.get("insights", "No insights provided"),
        }

    except Exception as e:
        print(f"[virality] Error calculating virality score for clip {clip_index}: {e}")
        return {
            "virality_score": 50,
            "hook_strength": 50,
            "emotional_impact": 50,
            "shareability": 50,
            "insights": f"Error calculating virality score: {str(e)}",
        }


def get_virality_label(score: int) -> str:
    """
    Get a human-readable label for a virality score.

    Args:
        score: Virality score (0-100)

    Returns:
        Label string
    """
    if score >= 80:
        return "🔥 Viral Potential"
    elif score >= 65:
        return "✨ High Engagement"
    elif score >= 50:
        return "👍 Good"
    elif score >= 35:
        return "📊 Average"
    else:
        return "⚠️ Needs Work"
