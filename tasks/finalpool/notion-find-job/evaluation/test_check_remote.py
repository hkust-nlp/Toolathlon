import unittest
from unittest.mock import Mock, patch

from check_remote import (
    _collect_paginated_results,
    get_database_entries,
    get_notion_page_blocks,
    get_notion_workspace_pages,
)


def _response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


class PaginationTests(unittest.TestCase):
    @patch('check_remote.requests.post')
    def test_workspace_search_collects_pages_after_first_hundred(self, post):
        first_hundred = [{'id': f'page-{index}'} for index in range(100)]
        job_finder = {'id': 'job-finder', 'title': 'Job Finder'}
        post.side_effect = [
            _response(
                {
                    'results': first_hundred,
                    'has_more': True,
                    'next_cursor': 'search-cursor',
                }
            ),
            _response(
                {
                    'results': [job_finder],
                    'has_more': False,
                    'next_cursor': None,
                }
            ),
        ]

        result = get_notion_workspace_pages('token', 'Job Finder')

        self.assertEqual(len(result['results']), 101)
        self.assertEqual(result['results'][-1], job_finder)
        self.assertEqual(post.call_args_list[0].kwargs['json']['page_size'], 100)
        self.assertEqual(
            post.call_args_list[0].kwargs['json']['query'],
            'Job Finder',
        )
        self.assertNotIn('start_cursor', post.call_args_list[0].kwargs['json'])
        self.assertEqual(
            post.call_args_list[1].kwargs['json']['start_cursor'],
            'search-cursor',
        )

    @patch('check_remote.requests.get')
    def test_block_children_pagination_uses_query_cursor(self, get):
        get.side_effect = [
            _response(
                {
                    'results': [{'id': 'block-1'}],
                    'has_more': True,
                    'next_cursor': 'block-cursor',
                }
            ),
            _response(
                {
                    'results': [{'id': 'block-2'}],
                    'has_more': False,
                    'next_cursor': None,
                }
            ),
        ]

        result = get_notion_page_blocks('page-id', 'token')

        self.assertEqual(
            [block['id'] for block in result['results']],
            ['block-1', 'block-2'],
        )
        self.assertEqual(
            get.call_args_list[1].kwargs['params']['start_cursor'],
            'block-cursor',
        )

    @patch('check_remote.requests.post')
    def test_database_query_pagination_uses_body_cursor(self, post):
        post.side_effect = [
            _response(
                {
                    'results': [{'id': 'job-1'}],
                    'has_more': True,
                    'next_cursor': 'database-cursor',
                }
            ),
            _response(
                {
                    'results': [{'id': 'job-2'}],
                    'has_more': False,
                    'next_cursor': None,
                }
            ),
        ]

        result = get_database_entries('database-id', 'token')

        self.assertEqual(
            [job['id'] for job in result['results']],
            ['job-1', 'job-2'],
        )
        self.assertEqual(
            post.call_args_list[1].kwargs['json']['start_cursor'],
            'database-cursor',
        )

    def test_missing_cursor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'without next_cursor'):
            _collect_paginated_results(
                lambda _cursor: {'results': [], 'has_more': True},
                'test resource',
            )

    def test_repeated_cursor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'repeated next_cursor'):
            _collect_paginated_results(
                lambda _cursor: {
                    'results': [],
                    'has_more': True,
                    'next_cursor': 'same-cursor',
                },
                'test resource',
            )


if __name__ == '__main__':
    unittest.main()
