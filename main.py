import logging
import asyncio
import aiohttp
import random
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SafeDanbooruBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.session = aiohttp.ClientSession()
        
        # SFW-теги (только безопасный контент)
        self.tags = {
            "waifu": ["rating:general", "1girl", "solo"],
            "neko": ["rating:general", "cat_ears", "1girl"],
            "maid": ["rating:general", "maid"],
            "landscape": ["rating:general", "scenery"]
        }
        
        self.base_url = "https://danbooru.donmai.us"

    async def get_safe_image(self, tags):
        try:
            params = {
                "tags": " ".join(tags),
                "random": "true",
                "limit": 1
            }
            
            async with self.session.get(
                f"{self.base_url}/posts.json",
                params=params,
                timeout=10
            ) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                return f"{self.base_url}{data[0]['file_url']}" if data and 'file_url' in data[0] else None
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

    def get_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        for tag in self.tags:
            keyboard.insert(InlineKeyboardButton(
                tag.capitalize(),
                callback_data=f"tag_{tag}"
            ))
        keyboard.add(InlineKeyboardButton("🎲 Случайное", callback_data="tag_random"))
        return keyboard

    async def send_image(self, chat_id, tag):
        image_url = await self.get_safe_image(self.tags[tag])
        if image_url:
            await self.bot.send_photo(chat_id, image_url, reply_markup=self.get_keyboard())
        else:
            await self.bot.send_message(chat_id, "🔍 Изображение не найдено", reply_markup=self.get_keyboard())

    def register_handlers(self):
        @self.dp.message_handler(commands=['start', 'menu'])
        async def cmd_start(message: types.Message):
            await message.answer("🌸 SFW Danbooru бот:", reply_markup=self.get_keyboard())

        @self.dp.callback_query_handler(lambda c: c.data.startswith('tag_'))
        async def process_tag(call: types.CallbackQuery):
            await call.answer()
            tag = call.data.split('_')[1]
            if tag == "random":
                tag = random.choice(list(self.tags.keys()))
            await self.send_image(call.from_user.id, tag)

    async def on_startup(self, dp):
        logger.info("Бот запущен")

    async def on_shutdown(self, dp):
        await self.session.close()
        logger.info("Бот остановлен")

    def run(self):
        self.register_handlers()
        executor.start_polling(
            self.dp,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown,
            skip_updates=True
        )

if __name__ == '__main__':
    bot = SafeDanbooruBot()
    bot.run()
