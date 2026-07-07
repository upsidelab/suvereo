import sqlglot
from sqlglot.errors import SqlglotError

from ecommerce_vertical.retrievers.errors import RetrieverSQLPermissionError


class SQLValidator:
    """Guards agent-generated SQL so it can only SELECT from the allowed table, and scopes it to a DataSet.

    Mirrors the Enthusiast SQL validator, adapted to the vertical's ``dataset_id`` column.
    """

    def __init__(self, allowed_table_name: str, data_set_id: int):
        self._allowed_table_name = allowed_table_name
        self._data_set_id = data_set_id

    def add_data_set_id_condition_and_raise_if_not_allowed(self, sql_query: str) -> str:
        """Validate the query and append a ``dataset_id`` condition scoping it to the current DataSet.

        Returns:
            The query with a WHERE condition for the data set id added.
        Raises:
            RetrieverSQLPermissionError: if the query is not a plain SELECT against the allowed table.
        """
        try:
            expression = sqlglot.parse_one(sql_query)
        except SqlglotError as e:
            raise RetrieverSQLPermissionError(f"Could not parse the SQL query because of the following error {e}.")

        if not isinstance(expression, sqlglot.exp.Select):
            raise RetrieverSQLPermissionError("Only SELECT queries are allowed.")

        subqueries = [node for node in expression.find_all(sqlglot.exp.Select) if node is not expression]
        if subqueries:
            raise RetrieverSQLPermissionError("Subqueries are not allowed.")

        if any(expression.find_all(sqlglot.exp.CTE)) or any(expression.find_all(sqlglot.exp.Subquery)):
            raise RetrieverSQLPermissionError("Subqueries or CTEs are not allowed.")

        for table in expression.find_all(sqlglot.exp.Table):
            if table.alias:
                raise RetrieverSQLPermissionError("Table aliases are not allowed.")

            table_name = table.name.lower()
            if table_name != self._allowed_table_name:
                raise RetrieverSQLPermissionError(f"Access to table '{table_name}' is forbidden.")

        expression_with_data_set_condition = expression.where(
            f"{self._allowed_table_name}.dataset_id = {self._data_set_id}"
        )
        return expression_with_data_set_condition.sql()
