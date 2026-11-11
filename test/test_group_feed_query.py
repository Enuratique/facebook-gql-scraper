import unittest
from unittest.mock import Mock, patch

from facebook_gql_scraper.facebookGraphql import (
    FacebookGraphQL,
    CometSinglePostDialogContentQueryGraphQL,
    GroupsCometFeedRegularStoriesPaginationQueryGraphQL,
)
from facebook_gql_scraper.structures import Group


class GroupFeedQueryTests(unittest.TestCase):
    def test_group_feed_includes_required_provider_variable(self):
        query = GroupsCometFeedRegularStoriesPaginationQueryGraphQL(Mock())
        with patch.object(FacebookGraphQL, "send") as send:
            query.send(groupId="123", cursor="next")
        variables = send.call_args.args[0]
        self.assertIs(variables["__relay_internal__pv__GeminiUFISaveToKnowledgeHubGKrelayprovider"], False)
        self.assertEqual(variables["id"], "123")
        self.assertEqual(variables["cursor"], "next")

    def test_single_post_includes_required_provider_variable(self):
        query = CometSinglePostDialogContentQueryGraphQL(Mock())
        with patch.object(FacebookGraphQL, "send") as send:
            query.send(postId="123")
        self.assertIs(send.call_args.args[0]["__relay_internal__pv__GeminiUFISaveToKnowledgeHubGKrelayprovider"], False)

    def test_group_posts_preserve_mentions_without_extra_metadata_request(self):
        mention = {"id": "42", "name": "Example"}
        item = {"id": "123", "creation_time": 1, "url": None, "title": None,
                "text": "hello", "mentions": [mention], "attachments": [],
                "share_count": 0, "comments_count": 0,
                "author": {"id": "1", "name": "Example", "url": None},
                "reactors_visible": False, "reactions": {"total": 0, "breakdown": []}}
        context = Mock()
        context.parse_graphql_response.return_value = {"parsed_data": {
            "posts": [item], "page_info": {"has_next_page": False, "end_cursor": None}}}
        with patch("facebook_gql_scraper.structures.GroupsCometFeedRegularStoriesPaginationQueryGraphQL") as query:
            query.return_value.send.return_value.text = "response"
            post = next(Group(context, {"id": "10"}).get_posts())
            with patch.object(post, "_obtain_metadata") as metadata:
                self.assertEqual(post.mentions, [mention])
                metadata.assert_not_called()


if __name__ == "__main__":
    unittest.main()
