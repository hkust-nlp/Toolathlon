import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

EVALUATION_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EVALUATION_DIR.parents[3]
for path in (str(REPOSITORY_ROOT), str(EVALUATION_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from check_local import (
    AMAZON_PRODUCT_PROBE,
    PRODUCT_TITLE_EXTRACTOR,
    _validate_products,
    _validate_url_in_session,
    build_amazon_fetch_probe,
    build_amazon_search_probe,
    check_product_requirements,
    extract_amazon_asin,
    find_js_content_from_result,
    normalize_amazon_url,
    normalize_usd_price,
    parse_page_probe_result,
    select_live_usd_price,
    warm_up_amazon_session,
)


def playwright_json_result(payload):
    # browser_evaluate serializes the JSON.stringify return value as a JSON
    # string inside the MCP result envelope.
    text = (
        '### Result\n'
        f'{json.dumps(json.dumps(payload))}\n\n'
        '### Ran Playwright code\n```js\nawait page.evaluate(...);\n```'
    )
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


class ProductTitleExtractionTests(unittest.TestCase):
    def test_product_title_uses_text_content(self):
        self.assertIn("getElementById('productTitle')", PRODUCT_TITLE_EXTRACTOR)
        self.assertIn('textContent', PRODUCT_TITLE_EXTRACTOR)
        self.assertNotIn('el.value', PRODUCT_TITLE_EXTRACTOR)

    def test_playwright_result_parser_preserves_title(self):
        title = 'TYBOATLE 88" W Black Faux Leather Sofa'
        result = (
            '### Result\n'
            f'{json.dumps(title)}\n\n'
            '### Ran Playwright code\n'
            '```js\nawait page.evaluate(...)\n```'
        )

        self.assertEqual(
            find_js_content_from_result(result),
            title,
        )


class LivePricePureFunctionTests(unittest.TestCase):
    def test_url_removes_currency_override_without_dropping_variant_options(self):
        url = 'https://www.amazon.com/example/dp/B0ABC12345?th=1&currency=EUR&psc=1'
        normalized = normalize_amazon_url(url)

        self.assertEqual(
            normalized,
            'https://www.amazon.com/dp/B0ABC12345?th=1&psc=1',
        )
        self.assertNotIn('currency=USD', normalized)
        self.assertEqual(extract_amazon_asin(normalized), 'B0ABC12345')

    def test_price_parser_handles_amazon_usd_formats(self):
        self.assertEqual(normalize_usd_price('$1,299.99', 'USD'), 1299.99)
        self.assertEqual(normalize_usd_price('US$ 369.99'), 369.99)
        self.assertEqual(normalize_usd_price(254.99, 'USD'), 254.99)

    def test_price_parser_rejects_ranges_and_foreign_currency(self):
        self.assertIsNone(normalize_usd_price('$199.99 - $249.99', 'USD'))
        self.assertIsNone(normalize_usd_price('€299.99'))
        self.assertIsNone(normalize_usd_price('299.99', 'EUR'))

    def test_selector_priority_and_currency_are_enforced(self):
        probe = {
            'currency': 'USD',
            'candidates': [
                {'text': '$299.99', 'source': 'core-price'},
                {'text': '$199.99', 'source': 'json-ld-offer'},
            ],
        }
        self.assertEqual(select_live_usd_price(probe), (299.99, 'core-price'))
        probe['currency'] = 'EUR'
        self.assertEqual(select_live_usd_price(probe), (None, None))

    def test_budget_is_strictly_less_than_400(self):
        passed, issues = check_product_requirements({'price': '$399.99'}, {'max_budget': 400})
        self.assertTrue(passed)
        self.assertEqual(issues, [])

        passed, issues = check_product_requirements({'price': '400.00'}, {'max_budget': 400})
        self.assertFalse(passed)
        self.assertIn('price < 400', issues[0])

    def test_probe_result_decodes_json_string(self):
        payload = {'productTitle': 'Black faux leather sofa', 'candidates': []}
        self.assertEqual(parse_page_probe_result(playwright_json_result(payload)), payload)

    def test_search_probe_is_constrained_to_exact_asin(self):
        function = build_amazon_search_probe('b0abc12345')
        self.assertIn('B0ABC12345', function)
        self.assertIn("getAttribute('data-asin')", function)
        self.assertIn('exactAsinMatched', function)

    def test_live_fetch_probe_is_constrained_to_canonical_exact_asin(self):
        function = build_amazon_fetch_probe(
            'https://www.amazon.com/title/dp/B0ABC12345?currency=EUR&tag=tracking',
            'B0ABC12345',
        )
        self.assertIn('https://www.amazon.com/dp/B0ABC12345', function)
        self.assertNotIn('currency=EUR', function)
        self.assertIn('declaredAsin.toUpperCase() === asin', function)
        self.assertIn("credentials: 'include'", function)

    def test_product_probe_has_bot_and_multiple_price_fallbacks(self):
        self.assertIn('Continue shopping gate', AMAZON_PRODUCT_PROBE)
        self.assertIn('corePriceDisplay_desktop_feature_div', AMAZON_PRODUCT_PROBE)
        self.assertIn('json-ld-offer', AMAZON_PRODUCT_PROBE)
        self.assertIn("'priceAmount'", AMAZON_PRODUCT_PROBE)
        self.assertIn('price-state-${key}', AMAZON_PRODUCT_PROBE)
        self.assertIn('declaredAsin', AMAZON_PRODUCT_PROBE)
        self.assertIn('input#ASIN, input[name="ASIN"]', AMAZON_PRODUCT_PROBE)


class LiveSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_warmup_sets_preferences_before_wait(self):
        fake_call = AsyncMock(return_value=SimpleNamespace(content=[]))
        with patch('utils.mcp.tool_servers.call_tool_with_retry', fake_call):
            await warm_up_amazon_session(object())

        self.assertEqual(
            [call.args[1] for call in fake_call.await_args_list],
            ['browser_navigate', 'browser_evaluate', 'browser_wait_for'],
        )
        self.assertEqual(
            fake_call.await_args_list[0].args[2],
            {'url': 'https://www.amazon.com/'},
        )

    async def test_detail_price_missing_uses_only_exact_asin_live_search(self):
        detail = {
            'productTitle': 'Black Faux Leather Sofa',
            'declaredAsin': 'B0ABC12345',
            'currency': 'USD',
            'candidates': [],
            'contentText': 'black faux leather sofa couch',
            'productPage': True,
            'botGate': False,
            'unavailable': False,
            'deliveryBlocked': False,
        }
        search = {
            'productTitle': 'Black Faux Leather Sofa',
            'currency': 'USD',
            'candidates': [
                {'text': '$299.99', 'source': 'amazon-search-exact-asin', 'currency': 'USD'}
            ],
            'contentText': 'black faux leather sofa',
            'exactAsinMatched': True,
            'botGate': False,
        }

        async def fake_call(_server, tool_name, arguments):
            if tool_name == 'browser_evaluate':
                if 'amazon-search-exact-asin' in arguments['function']:
                    return playwright_json_result(search)
                return playwright_json_result(detail)
            return SimpleNamespace(content=[])

        fake = AsyncMock(side_effect=fake_call)
        with patch('utils.mcp.tool_servers.call_tool_with_retry', fake):
            ok, error, response = await _validate_url_in_session(
                'https://www.amazon.com/example/dp/B0ABC12345?currency=USD', object()
            )

        self.assertTrue(ok, error)
        self.assertEqual(response['extracted_price'], 299.99)
        self.assertEqual(response['price_source'], 'amazon-search-exact-asin')
        navigations = [
            call.args[2]['url'] for call in fake.await_args_list
            if call.args[1] == 'browser_navigate'
        ]
        self.assertNotIn('currency=USD', navigations[0])
        self.assertEqual(navigations[-1], 'https://www.amazon.com/s?k=B0ABC12345')

    async def test_same_session_live_fetch_precedes_search_fallback(self):
        detail = {
            'productTitle': 'Black Faux Leather Sofa',
            'declaredAsin': 'B0ABC12345',
            'currency': 'USD',
            'candidates': [],
            'contentText': 'black faux leather sofa',
            'productPage': True,
            'botGate': False,
            'unavailable': False,
        }
        fetched = {
            **detail,
            'exactAsinMatched': True,
            'candidates': [
                {'text': '$299.98', 'source': 'live-fetch-core-price', 'currency': 'USD'}
            ],
        }

        async def fake_call(_server, tool_name, arguments):
            if tool_name == 'browser_evaluate':
                if 'live-fetch-core-price' in arguments['function']:
                    return playwright_json_result(fetched)
                return playwright_json_result(detail)
            return SimpleNamespace(content=[])

        fake = AsyncMock(side_effect=fake_call)
        with patch('utils.mcp.tool_servers.call_tool_with_retry', fake):
            ok, error, response = await _validate_url_in_session(
                'https://www.amazon.com/example/dp/B0ABC12345', object()
            )

        self.assertTrue(ok, error)
        self.assertEqual(response['extracted_price'], 299.98)
        self.assertEqual(response['price_source'], 'live-fetch-core-price')
        navigations = [
            call.args[2]['url'] for call in fake.await_args_list
            if call.args[1] == 'browser_navigate'
        ]
        self.assertEqual(navigations, [])
        self.assertEqual(fake.await_args_list[0].args[1], 'browser_evaluate')
        self.assertIn('live-fetch-core-price', fake.await_args_list[0].args[2]['function'])

    async def test_wrong_detail_asin_is_rejected_and_search_continues(self):
        fetch_miss = {
            'botGate': False,
            'exactAsinMatched': False,
            'candidates': [],
        }
        wrong_detail = {
            'productTitle': 'Wrong Variant Black Sofa',
            'declaredAsin': 'B0WRONG999',
            'currency': 'USD',
            'candidates': [
                {'text': '$111.11', 'source': 'core-price', 'currency': 'USD'}
            ],
            'contentText': 'black faux leather sofa',
            'productPage': True,
            'botGate': False,
            'unavailable': False,
        }
        search = {
            'productTitle': 'Correct Black Faux Leather Sofa',
            'currency': 'USD',
            'candidates': [
                {'text': '$299.96', 'source': 'amazon-search-exact-asin', 'currency': 'USD'}
            ],
            'contentText': 'correct black faux leather sofa',
            'exactAsinMatched': True,
            'botGate': False,
        }

        async def fake_call(_server, tool_name, arguments):
            if tool_name == 'browser_evaluate':
                function = arguments['function']
                if 'amazon-search-exact-asin' in function:
                    return playwright_json_result(search)
                if 'live-fetch-core-price' in function:
                    return playwright_json_result(fetch_miss)
                return playwright_json_result(wrong_detail)
            return SimpleNamespace(content=[])

        fake = AsyncMock(side_effect=fake_call)
        with patch('utils.mcp.tool_servers.call_tool_with_retry', fake):
            ok, error, response = await _validate_url_in_session(
                'https://www.amazon.com/dp/B0ABC12345', object()
            )

        self.assertTrue(ok, error)
        self.assertEqual(response['extracted_price'], 299.96)
        self.assertEqual(response['price_source'], 'amazon-search-exact-asin')
        self.assertFalse(response['exact_asin_detail_match'])
        self.assertTrue(any(
            'navigated product page: target ASIN was not confirmed' in failure
            for failure in response['surface_failures']
        ))

    async def test_fetch_bot_gate_falls_back_to_navigated_product_page(self):
        fetch_gate = {
            'botGate': True,
            'botReason': 'Amazon live-fetch CAPTCHA/Continue shopping gate',
            'exactAsinMatched': False,
            'candidates': [],
        }
        detail = {
            'productTitle': 'Black Faux Leather Sofa',
            'declaredAsin': 'B0ABC12345',
            'currency': 'USD',
            'candidates': [
                {'text': '$299.97', 'source': 'core-price', 'currency': 'USD'}
            ],
            'contentText': 'black faux leather sofa',
            'productPage': True,
            'botGate': False,
            'unavailable': False,
        }

        async def fake_call(_server, tool_name, arguments):
            if tool_name == 'browser_evaluate':
                if 'live-fetch-core-price' in arguments['function']:
                    return playwright_json_result(fetch_gate)
                return playwright_json_result(detail)
            return SimpleNamespace(content=[])

        fake = AsyncMock(side_effect=fake_call)
        with patch('utils.mcp.tool_servers.call_tool_with_retry', fake):
            ok, error, response = await _validate_url_in_session(
                'https://www.amazon.com/dp/B0ABC12345', object()
            )

        self.assertTrue(ok, error)
        self.assertEqual(response['extracted_price'], 299.97)
        self.assertEqual(response['price_source'], 'core-price')
        self.assertTrue(response['bot_gate'])
        self.assertTrue(any('live-fetch' in failure for failure in response['surface_failures']))

    async def test_duplicate_asins_fail_and_delivery_location_is_diagnostic_only(self):
        products = [
            {
                'canonical_url': f'https://www.amazon.com/dp/{asin}',
                'title': 'Black Faux Leather Sofa',
                'price': '299.99',
                'store_name': 'Example',
            }
            for asin in ('B0ABC12345', 'B0ABC12345', 'B0XYZ67890')
        ]
        response = {
            'extracted_price': 299.99,
            'price_source': 'core-price',
            'extracted_title': 'Black Faux Leather Sofa',
            'content_preview': 'black faux leather sofa couch',
            'can_deliver': False,
            'in_stock': True,
        }
        validator = AsyncMock(return_value=(True, '', response))
        with patch('check_local.validate_url_with_playwright_mcp', validator):
            valid_count, issues = await _validate_products(products, object())

        self.assertEqual(valid_count, 1)
        self.assertEqual(sum('Duplicate ASIN B0ABC12345' in issue for issue in issues), 2)
        self.assertFalse(any('deliver' in issue.lower() for issue in issues))


if __name__ == '__main__':
    unittest.main()
