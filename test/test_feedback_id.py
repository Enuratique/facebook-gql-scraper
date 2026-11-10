import base64
import unittest
from unittest.mock import Mock, patch

from facebook_gql_scraper.facebookGraphql import (
    CommentsListComponentsPaginationQueryGraphQL, Depth1CommentsListPaginationQueryGraphQL, FacebookGraphQL,
)
from facebook_gql_scraper.structures import Comment, Post
from facebook_gql_scraper.unifiedFacebookParser import _parse_feed_post, parse_post, parse_facebook_comments


class FeedbackIdTests(unittest.TestCase):
    def test_comments_query_prefers_returned_id_and_keeps_legacy_fallback(self):
        query = CommentsListComponentsPaginationQueryGraphQL(Mock())
        with patch.object(FacebookGraphQL, "send") as send:
            query.send("123", feedbackId="facebook-feedback", commentsAfterCursor="cursor")
            self.assertEqual(send.call_args.args[0]["id"], "facebook-feedback")
            self.assertEqual(send.call_args.args[0]["commentsAfterCursor"], "cursor")
            query.send("123")
            self.assertEqual(send.call_args.args[0]["id"], base64.b64encode(b"feedback:123").decode())

    def test_both_post_parsers_preserve_comment_list_feedback(self):
        target = {"comment_list_renderer": {"feedback": {"id": "actual-id"}}}
        sections = {"feedback": {"story": {"story_ufi_container": {"story": {
            "feedback_context": {"feedback_target_with_context": target}}}}}}
        node = {"post_id": "123", "comet_sections": sections}
        with patch("facebook_gql_scraper.unifiedFacebookParser._parse_reactions_from_ufi", return_value=({}, None, 0)):
            self.assertEqual(_parse_feed_post({"node": node})["feedback_id"], "actual-id")
            self.assertEqual(parse_post({"data": {"node_v2": node}})["post"]["feedback_id"], "actual-id")

    def test_post_fetches_metadata_when_feed_omits_feedback_id(self):
        context = Mock()
        context.parse_graphql_response.return_value = {"parsed_data": {
            "comments": [], "page_info": {"has_next_page": False, "end_cursor": None}}}
        post = Post(context, {"id": "123"})

        def fetch_metadata():
            post._data["feedback_id"] = "actual-id"
            post._full_fetched = True

        with patch.object(post, "_obtain_metadata", side_effect=fetch_metadata) as metadata, \
             patch("facebook_gql_scraper.structures.CommentsListComponentsPaginationQueryGraphQL") as query:
            query.return_value.send.return_value.text = "response"
            self.assertEqual(list(post.get_comments()), [])
            metadata.assert_called_once()
            self.assertEqual(query.return_value.send.call_args.kwargs["feedbackId"], "actual-id")

    def test_comment_feedback_survives_parser_and_is_used_for_replies(self):
        encoded = base64.b64encode(b"comment:123_456").decode()
        payload = {"data": {"node": {"comment_rendering_instance_for_feed_location": {
            "comments": {"edges": [{"node": {"id": encoded, "feedback": {
                "id": "comment-feedback", "replies_fields": {"total_count": 1}}}}]}}}}}
        comment_data = parse_facebook_comments(payload)["comments"][0]
        self.assertEqual(comment_data["feedback_id"], "comment-feedback")
        context = Mock()
        context.parse_graphql_response.return_value = {"parsed_data": {
            "replies": [], "page_info": {"has_next_page": False, "end_cursor": None}}}
        comment = Comment(context, comment_data, post=Post(context, {"id": "123"}))
        with patch("facebook_gql_scraper.structures.Depth1CommentsListPaginationQueryGraphQL") as query:
            query.return_value.send.return_value.text = "response"
            self.assertEqual(list(comment.get_replies()), [])
            self.assertEqual(query.return_value.send.call_args.kwargs["feedbackId"], "comment-feedback")
        query = Depth1CommentsListPaginationQueryGraphQL(context)
        with patch.object(FacebookGraphQL, "send") as send:
            query.send("123", "456", "token", feedbackId="comment-feedback")
            self.assertEqual(send.call_args.args[0]["id"], "comment-feedback")
            query.send("123", "456", "token")
            self.assertEqual(send.call_args.args[0]["id"], base64.b64encode(b"feedback:123_456").decode())


if __name__ == "__main__":
    unittest.main()
