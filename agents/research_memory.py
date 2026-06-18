import sqlite3
import os

def get_similar_past_responses(
    db_path: str,
    business_id: str,
    rating: int,
    limit: int = 3
) -> list[dict]:
    """
    Fetch approved responses for the same business at similar rating levels.
    Used to calibrate tone and avoid repeated openers.
    """
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT r2.text as review_text, rsp.response_text, rsp.qa_score,
                   GROUP_CONCAT(rtt.tag) as tone_tags
            FROM responses rsp
            JOIN reviews r2 ON rsp.review_id = r2.id
            LEFT JOIN response_tone_tags rtt ON rsp.id = rtt.response_id
            WHERE r2.business_id = ?
              AND r2.rating BETWEEN ? AND ?
              AND rsp.approved_by IS NOT NULL
            GROUP BY rsp.id
            ORDER BY rsp.published_at DESC
            LIMIT ?
        """, (business_id, max(1, rating - 1), min(5, rating + 1), limit))

        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    return [dict(row) for row in rows]


def save_approved_response(db_path: str, envelope: dict):
    """Called by Escalation/Monitor after a response is published."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO reviews (id, business_id, platform, rating, text, author, review_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        envelope["review_id"], envelope["business_id"], envelope["platform"],
        envelope["review"]["rating"], envelope["review"]["text"],
        envelope["review"].get("author"), envelope["review"]["timestamp"]
    ))

    cursor.execute("""
        INSERT INTO responses (review_id, response_text, qa_score, approved_by, published_at, version)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
    """, (
        envelope["review_id"], envelope["final_response"],
        envelope.get("qa", {}).get("overall_score"), "auto",
        envelope.get("draft", {}).get("version", 1)
    ))

    conn.commit()
    conn.close()
