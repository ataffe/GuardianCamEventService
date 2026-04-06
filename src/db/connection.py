from sqlalchemy import create_engine


def get_engine(config):
    url = (
        f"postgresql+psycopg://{config['db']['user']}"
        f"@{config['db']['host']}:{config['db']['port']}/{config['db']['name']}"
    )
    return create_engine(url=url, echo=False)