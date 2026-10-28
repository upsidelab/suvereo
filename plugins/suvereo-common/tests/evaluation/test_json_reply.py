from suvereo_common.evaluation.json_reply import JsonReply


class TestJsonReply:
    def test_finds_every_object_in_the_prose_around_it(self):
        reply = 'Sure: {"a": 1} and then {"b": {"c": 2}}. Done.'

        assert list(JsonReply.objects(reply)) == [{"a": 1}, {"b": {"c": 2}}, {"c": 2}]

    def test_skips_broken_json_and_other_values(self):
        assert list(JsonReply.objects('{oops} [1, 2] {"ok": true')) == []
