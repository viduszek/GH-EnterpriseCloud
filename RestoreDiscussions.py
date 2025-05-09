import requests
import json
import time
from tqdm import tqdm

# === CONFIG ===
TOKEN = "ghp_your_token_here"  # <-- Replace with GitHub token
OWNER = "target_org"           # <-- e.g., "your-org"
REPO = "target_repo"           # <-- e.g., "new-repo"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
API_URL = "https://api.github.com/graphql"
INPUT_FILE = "discussions.json"

def run_query(query, variables):
    response = requests.post(API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Query failed: {response.status_code} {response.text}")
    return response.json()


def get_category_map():
    """Fetch category name → ID from the target repo."""
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        discussionCategories(first: 100) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    result = run_query(query, {"owner": OWNER, "repo": REPO})
    categories = result["data"]["repository"]["discussionCategories"]["nodes"]
    return {cat["name"]: cat["id"] for cat in categories}


def create_discussion(title, body, category_id):
    query = """
    mutation($repoId: ID!, $title: String!, $body: String!, $categoryId: ID!) {
      createDiscussion(input: {
        repositoryId: $repoId,
        title: $title,
        body: $body,
        categoryId: $categoryId
      }) {
        discussion {
          number
          id
        }
      }
    }
    """
    repo_id = get_repo_id()
    variables = {
        "repoId": repo_id,
        "title": title,
        "body": body,
        "categoryId": category_id
    }
    result = run_query(query, variables)
    return result["data"]["createDiscussion"]["discussion"]["number"]


def get_repo_id():
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        id
      }
    }
    """
    result = run_query(query, {"owner": OWNER, "repo": REPO})
    return result["data"]["repository"]["id"]


def add_comment(discussion_number, body):
    query = """
    mutation($repo: String!, $owner: String!, $number: Int!, $body: String!) {
      addDiscussionComment(input: {
        repositoryName: $repo,
        repositoryOwner: $owner,
        discussionNumber: $number,
        body: $body
      }) {
        comment {
          id
        }
      }
    }
    """
    result = run_query(query, {
        "owner": OWNER,
        "repo": REPO,
        "number": discussion_number,
        "body": body
    })
    return result["data"]["addDiscussionComment"]["comment"]["id"]


def add_reply(comment_id, body):
    query = """
    mutation($body: String!, $commentId: ID!) {
      addDiscussionReply(input: {
        body: $body,
        commentId: $commentId
      }) {
        reply {
          id
        }
      }
    }
    """
    result = run_query(query, {
        "body": body,
        "commentId": comment_id
    })
    return result["data"]["addDiscussionReply"]["reply"]["id"]


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        discussions = json.load(f)

    category_map = get_category_map()

    print(f"Restoring {len(discussions)} discussions to {OWNER}/{REPO}...\n")

    for discussion in tqdm(discussions):
        title = discussion["title"]
        body = discussion["body"]
        category_name = discussion["category"]["name"]
        category_id = category_map.get(category_name)

        if not category_id:
            print(f"❌ Category '{category_name}' not found in target repo. Skipping discussion '{title}'")
            continue

        discussion_number = create_discussion(title, body, category_id)

        for comment in discussion["comments"]:
            comment_id = add_comment(discussion_number, comment["body"])
            for reply in comment.get("replies", []):
                add_reply(comment_id, reply["body"])
                time.sleep(0.5)  # To avoid abuse detection

        time.sleep(1)  # Delay between discussions

    print("✅ Restore complete.")


if __name__ == "__main__":
    main()
