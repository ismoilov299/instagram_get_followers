from aiogram.fsm.state import State, StatesGroup

class InstagramStates(StatesGroup):
    waiting_username = State()