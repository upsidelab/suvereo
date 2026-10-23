from pathlib import Path

import pytest
from enthusiast_common.evaluation.cases import CsvCaseSource
from enthusiast_common.evaluation.errors import CaseSourceError


def _csv(tmp_path: Path, text: str, *files: str) -> Path:
    for file in files:
        (tmp_path / file).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / file).write_bytes(b"x")
    path = tmp_path / "cases.csv"
    path.write_text(text, encoding="utf-8")
    return path


class TestCsvCaseSource:
    def test_reads_the_documented_example(self, tmp_path):
        path = _csv(
            tmp_path,
            "id,files,expected.mock_calls.create_order_with_items.0.items,tags\n"
            'simple,cases/simple.pdf,"[[""SKU-1"",2],[""SKU-7"",1]]",basic\n'
            'photo,cases/photo.png,"[[""SKU-3"",5]]",image;blurry\n',
            "cases/simple.pdf",
            "cases/photo.png",
        )

        simple, photo = CsvCaseSource(path).load()

        assert simple.id == "simple"
        assert simple.files == [(tmp_path / "cases/simple.pdf").resolve()]
        assert simple.expected == {"mock_calls": {"create_order_with_items": [{"items": [["SKU-1", 2], ["SKU-7", 1]]}]}}
        assert photo.tags == ["image", "blurry"]

    def test_cells_starting_like_json_are_parsed_and_others_stay_text(self, tmp_path):
        path = _csv(
            tmp_path,
            "id,input.count,input.flag,input.items,input.meta,input.quoted\n"
            'c,3,true,"[1, 2]","{""a"": 1}","""text"""\n',
        )

        case = CsvCaseSource(path).load()[0]

        assert case.input == {"count": "3", "flag": "true", "items": [1, 2], "meta": {"a": 1}, "quoted": "text"}

    def test_number_like_identifiers_keep_their_exact_text(self, tmp_path):
        path = _csv(tmp_path, "id,input.order_number,expected.output.sku\nc,12345,00123\n")

        case = CsvCaseSource(path).load()[0]

        assert case.input == {"order_number": "12345"}
        assert case.expected == {"output": {"sku": "00123"}}

    def test_empty_cells_are_left_out_and_other_columns_go_to_extra(self, tmp_path):
        path = _csv(tmp_path, "id,description,input.note,difficulty\nc,,,hard\n")

        case = CsvCaseSource(path).load()[0]

        assert case.description == ""
        assert case.input == {}
        assert case.extra == {"difficulty": "hard"}

    def test_spaces_around_header_names_are_ignored(self, tmp_path):
        path = _csv(tmp_path, " id , input.note \nc,hello\n")

        assert CsvCaseSource(path).load()[0].input == {"note": "hello"}

    def test_a_spreadsheet_byte_order_mark_is_ignored(self, tmp_path):
        path = tmp_path / "cases.csv"
        path.write_text("id,description\nc,from excel\n", encoding="utf-8-sig")

        assert CsvCaseSource(path).load()[0].id == "c"

    def test_reads_conversation_cases(self, tmp_path):
        path = _csv(
            tmp_path,
            "id,turns,user.goal,user.max_turns\n"
            "split,Hi;Under 50 EUR,,\n"
            'json,"[""Hi; I need a kettle"", ""Under 50 EUR""]",,\n'
            "simulated,,Find a kettle,6\n",
        )

        split, json, simulated = CsvCaseSource(path).load()

        assert split.turns == ["Hi", "Under 50 EUR"]
        assert json.turns == ["Hi; I need a kettle", "Under 50 EUR"]
        assert (simulated.user.goal, simulated.user.max_turns) == ("Find a kettle", 6)
        assert split.user is None

    @pytest.mark.parametrize(
        "text, row, column, message",
        [
            ("description\nx\n", 1, None, "'id' column"),
            ("id,input.\nc,1\n", 1, "input.", "field name"),
            ("id,description\nok,fine\n,missing id\n", 3, None, "id"),
            ("id,files\nc,missing.pdf\n", 2, None, "does not exist"),
            ("id,expected.a,expected.a.b\nc,1,2\n", 2, "expected.a.b", "also used as a path"),
            ("id,expected.items.0,expected.items.x\nc,1,2\n", 2, "expected.items.x", "must be a number"),
            ("id\nc,extra-cell\n", 2, None, "more cells"),
            ("id,expected.items.0,expected.items.0.sku\nc,1,X\n", 2, "expected.items.0.sku", "also used as a path"),
            ('id,expected.items\nc,"[1,"\n', 2, "expected.items", "does not parse"),
            ("id,difficulty\nc,{oops\n", 2, "difficulty", "does not parse"),
            ("id,expected.a, expected.a\nc,1,2\n", 1, "expected.a", "more than once"),
            ("id,user.\nc,1\n", 1, "user.", "field name"),
            ('id,turns\nc,"[""Hi"","\n', 2, "turns", "does not parse"),
            ("id,user.persona\nc,terse\n", 2, None, "goal"),
        ],
    )
    def test_errors_name_the_row_and_column(self, tmp_path, text, row, column, message):
        with pytest.raises(CaseSourceError, match=message) as e:
            CsvCaseSource(_csv(tmp_path, text)).load()

        assert e.value.row == row
        assert e.value.column == column
