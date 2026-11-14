from chatbot.database import Base
from sqlalchemy import Column, Integer, String, Boolean

class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    mail = Column(String, unique=True, index=True, nullable=False)
    otp = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)