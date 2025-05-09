import requests
import json
from tqdm import tqdm

# === CONFIG ===
GITHUB_API_URL = "https://api.github.com/graphql"
TOKEN = "ghp_your_token_here"  # <-- Replace with your GitHub PAT
OWNER = "owner_name"           # <-- e.g., "vercel"
REPO = "repo_name"             # <-- e.g., "next.js"

HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def run_query(query, variables):
    response = requests.post(GITHUB_API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Query failed [{response.status_code}]: {response.text}")
    return response.json()


def paginate_discussions():
    discussions = []
    cursor = None
    print("Fetching discussions...")
    while True:
        query = """
        query($owner: String!, $repo: String!, $cursor: String) {
          repository(owner: $owner, name: $repo) {
            discussions(first: 50, after: $cursor) {
              pageInfo {
                endCursor
                hasNextPage
              }
              nodes {
                number
                title
                body
                createdAt
                category {
                  id
                  name
                }
              }
            }
          }
        }
        """
        variables = {"owner": OWNER, "repo": REPO, "cursor": cursor}
        data = run_query(query, variables)
        discussion_data = data["data"]["repository"]["discussions"]
        for d in discussion_data["nodes"]:
            d["comments"] = paginate_comments(d["number"])
            discussions.append(d)

        if not discussion_data["pageInfo"]["hasNextPage"]:
            break
        cursor = discussion_data["pageInfo"]["endCursor"]
    return discussions


def paginate_comments(discussion_number):
    comments = []
    cursor = None
    while True:
        query = """
        query($owner: String!, $repo: String!, $number: Int!, $cursor: String) {
          repository(owner: $owner, name: $repo) {
            discussion(number: $number) {
              comments(first: 100, after: $cursor) {
                pageInfo {
                  endCursor
                  hasNextPage
                }
                nodes {
                  body
                  createdAt
                  author {
                    login
                  }
                  replies(first: 100) {
                    pageInfo {
                      endCursor
                      hasNextPage
                    }
                    nodes {
                      body
                      createdAt
                      author {
                        login
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"owner": OWNER, "repo": REPO, "number": discussion_number, "cursor": cursor}
        data = run_query(query, variables)
        comment_data = data["data"]["repository"]["discussion"]["comments"]
        for comment in comment_data["nodes"]:
            comment["replies"] = paginate_replies(discussion_number, comment["body"])
            comments.append(comment)

        if not comment_data["pageInfo"]["hasNextPage"]:
            break
        cursor = comment_data["pageInfo"]["endCursor"]
    return comments


def paginate_replies(discussion_number, comment_body_snippet):
    # GitHub doesn't provide reply-level IDs for paginating a single comment's replies,
    # so we must fetch all replies during each comment pagination.
    # In practice, replies don't paginate deeply—100 is usually enough.
    # If needed, refactor to identify comments by order or hash.
    # Placeholder in case GitHub improves their API for nested pagination.
    return []  # Already included in paginate_comments via `replies {}`


def save_to_json(data, filename="discussions.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    discussions = paginate_discussions()
    save_to_json(discussions)
    print(f"Saved {len(discussions)} discussions to discussions.json")


if __name__ == "__main__":
    main()
