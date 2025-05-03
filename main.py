import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN, DANBOORU_API_KEY, DANBOORU_USER
import random

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DanbooruBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.session = aiohttp.ClientSession()
        self.tags = {
            "waifu": ["1girl", "solo"],
            "neko": ["cat_ears", "1girl"],
            "maid": ["maid", "1girl"],
            "nsfw": ["rating:explicit", "1girl"]
        }
        self.base_url = "https://danbooru.donmai.us"
        
    async def get_danbooru_image(self, tags):
        try:
            params = {
                "tags": " ".join(tags),
                "random": "true",
                "limit": 1
            }
            
            if DANBOORU_API_KEY and DANBOORU_USER:
                params["login"] = DANBOORU_USER
                params["api_key"] = DANBOORU_API_KEY
            
            async with self.session.get(
                f"{self.base_url}/posts.json",
                params=params,
                timeout=10
            ) as response:
                if response.status != 200:
                    logger.error(f"Danbooru API error: {response.status}")
                    return None
                
                data = await response.json()
                if not data:
                    return None
                
                post = data[0]
                if "file_url" not in post:
                    return None
                    
                return f"{self.base_url}{post['file_url']}"
                
        except Exception as e:
            logger.error(f"Danbooru request failed: {e}")
            return None

    def get_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        for tag in self.tags:
            if tag != "nsfw":
                keyboard.insert(InlineKeyboardButton(
                    tag.capitalize(),
                    callback_data=f"tag_{tag}"
                ))
        keyboard.row(
            InlineKeyboardButton("🔞 NSFW", callback_data="tag_nsfw"),
            InlineKeyboardButton("🎲 Random", callback_data="tag_random")
        )
        return keyboard

    async def send_post(self, chat_id, tags):
        image_url = await self.get_danbooru_image(tags)
        if image_url:
            try:
                await self.bot.send_photo(
                    chat_id,
                    image_url,
                    reply_markup=self.get_keyboard()
                )
            except Exception as e:
                logger.error(f"Send photo error: {e}")
                await self.bot.send_message(
                    chat_id,
                    "⚠️ Не удалось отправить изображение",
                    reply_markup=self.get_keyboard()
                )
        else:
            await self.bot.send_message(
                chat_id,
                "⚠️ Не найдено подходящих изображений",
                reply_markup=self.get_keyboard()
            )

    def register_handlers(self):
        @self.dp.message_handler(commands=['start'])
        async def cmd_start(message: types.Message):
            await message.answer(
                "🎌 Danbooru бот готов к работе!",
                reply_markup=self.get_keyboard()
            )

        @self.dp.callback_query_handler(lambda c: c.data.startswith('tag_'))
        async def process_tag(call: types.CallbackQuery):
            await call.answer()
            tag = call.data.split('_')[1]
            
            if tag == "random":
                tag = random.choice(list(self.tags.keys()))
                
            await self.send_post(call.from_user.id, self.tags[tag])

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
    bot = DanbooruBot()
    bot.run()
