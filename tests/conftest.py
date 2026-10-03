import pytest

from src.utils.spark import create_spark


@pytest.fixture(scope="session")
def spark():
    session = create_spark()
    yield session
    session.stop()
