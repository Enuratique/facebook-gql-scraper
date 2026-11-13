import unittest
from unittest.mock import Mock

from facebook_gql_scraper.exceptions import FacebookResponseParseError, PostNotFoundError, PostUnavailableError
from facebook_gql_scraper.structures import Post
from facebook_gql_scraper.unifiedFacebookParser import parse_facebook_payload


class UnavailablePostTests(unittest.TestCase):
    def test_unparseable_response_is_not_treated_as_unavailable(self):
        context = Mock()
        context.parse_graphql_response.return_value = None
        with self.assertRaisesRegex(FacebookResponseParseError, "post 123"):
            Post(context, {"id": "123"})._obtain_metadata()

    def test_null_node_without_error_is_unavailable(self):
        parsed = parse_facebook_payload({"data": {"node_v2": None}})
        self.assertIsNone(parsed["parsed_data"])
        self.assertTrue(parsed["post_unavailable"])
        context = Mock()
        context.parse_graphql_response.return_value = parsed
        with self.assertRaises(PostUnavailableError):
            Post(context, {"id": "123"})._obtain_metadata()

    def test_null_node_with_graphql_error_is_not_classified_as_unavailable(self):
        parsed = parse_facebook_payload({"data": {"node_v2": None}, "errors": [{"message": "error"}]})
        self.assertFalse(parsed["post_unavailable"])
        context = Mock()
        context.parse_graphql_response.return_value = parsed
        with self.assertRaises(PostNotFoundError) as caught:
            Post(context, {"id": "123"})._obtain_metadata()
        self.assertNotIsInstance(caught.exception, PostUnavailableError)
