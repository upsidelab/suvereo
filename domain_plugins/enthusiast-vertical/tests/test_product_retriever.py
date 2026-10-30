from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import FieldDoesNotExist
from django.db import DataError, OperationalError, ProgrammingError
from enthusiast_vertical.models import Product
from enthusiast_vertical.retrievers.product import ProductRetriever
from enthusiast_vertical.retrievers.retriever_sql_execution_error import RetrieverSQLExecutionError
from model_bakery import baker

from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class TestProductRetrieverFindProductsWithSql:
    @pytest.mark.parametrize(
        "error",
        [
            FieldDoesNotExist("Raw query must include the primary key"),
            ProgrammingError('column "colour" does not exist'),
            DataError("invalid input syntax for type double precision"),
        ],
    )
    def test_raises_an_agent_friendly_error_with_the_reason(self, error):
        retriever = ProductRetriever(data_set_id=1, llm=MagicMock())

        with patch.object(Product.objects, "raw", return_value=MagicMock(__iter__=MagicMock(side_effect=error))):
            with pytest.raises(RetrieverSQLExecutionError) as raised:
                retriever.find_products_with_sql("SELECT name FROM enthusiast_vertical_product")

        assert raised.value.__cause__ is error
        assert str(error) in raised.value.agent_friendly_message

    def test_lets_infrastructure_errors_through(self):
        retriever = ProductRetriever(data_set_id=1, llm=MagicMock())
        error = OperationalError("server closed the connection unexpectedly")

        with patch.object(Product.objects, "raw", return_value=MagicMock(__iter__=MagicMock(side_effect=error))):
            with pytest.raises(OperationalError):
                retriever.find_products_with_sql("SELECT id FROM enthusiast_vertical_product")


class TestProductRetrieverInATransaction:
    def test_a_failed_query_leaves_the_transaction_usable_for_a_retry(self):
        data_set = baker.make(DataSet)
        baker.make(Product, dataset=data_set)
        retriever = ProductRetriever(data_set_id=data_set.id, llm=MagicMock())

        with pytest.raises(RetrieverSQLExecutionError):
            retriever.find_products_with_sql("SELECT id, colour FROM enthusiast_vertical_product")

        assert len(retriever.find_products_with_sql("SELECT id, name FROM enthusiast_vertical_product")) == 1


class TestRetrieverSQLExecutionError:
    def test_message_has_the_reason_without_a_chained_cause(self):
        assert "bad column" in RetrieverSQLExecutionError(ProgrammingError("bad column")).agent_friendly_message
