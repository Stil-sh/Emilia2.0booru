import logging
import asyncio
import aiohttp
import random
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN, DANBOORU_API_KEY, DANBOORU_USER

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
        self.base_url = "https://danbooru.donmai.us"
        
        # SFW-категории с минимальным рейтингом
        self.categories = {
            "waifu": ["rating:general", "1girl", "solo"],
            "neko": ["rating:general", "cat_ears"],
            "nature": ["rating:general", "landscape"],
            "food": ["rating:general", "food"]
        }

    async def get_danbooru_post(self, tags):
        """Безопасный запрос к Danbooru API"""
        try:
            params = {
                "tags": " ".join(tags),
                "random": "true",
                "limit": 1
            }
            
            # Добавляем авторизацию если есть ключи
            if DANBOORU_API_KEY and DANBOORU_USER:
                params.update({
                    "login": DANBOORU_USER,
                    "api_key": DANBOORU_API_KEY
                })
            
            async with self.session.get(
                f"{self.base_url}/posts.json",
                params=params,
                timeout=10
            ) as resp:
                if resp.status != 200:
                    logger.error(f"API Error: {resp.status}")
                    return None
                    
                data = await resp.json()
                return data[0] if data else None
                
        except Exception as e:
            logger.error(f"Danbooru error: {e}")
            return None

    async def safe_send_image(self, chat_id, tags):
        """Безопасная отправка с обработкой ошибок"""
        try:
            post = await self.get_danbooru_post(tags)
            if not post or "file_url" not in post:
                await self.bot.send_message(chat_id, "🌐 Ничего не найдено")
                return
                
            # Проверяем рейтинг на всякий случай
            if post.get("rating") != "g":
                logger.warning(f"Filtered non-SFW content: {post.get('id')}")
                await self.bot.send_message(chat_id, "⚠️ Контент отфильтрован")
                return
                
            await self.bot.send_photo(
                chat_id,
                f"{self.base_url}{post['file_url']}",
                reply_markup=self.get_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            await self.bot.send_message(chat_id, "⚠️ Ошибка загрузки")

    def get_keyboard(self):
        kb = InlineKeyboardMarkup(row_width=2)
        for cat in self.categories:
            kb.insert(InlineKeyboardButton(
                cat.capitalize(),
                callback_data=f"cat_{cat}"
            ))
        kb.add(InlineKeyboardButton("🎲 Random", callback_data="cat_random"))
        return kb

    def register_handlers(self):
        @self.dp.message_handler(commands=['start'])
        async def cmd_start(message: types.Message):
            await message.answer(
                "🎌 SFW Danbooru Бот\nВыберите категорию:",
                reply_markup=self.get_keyboard()
            )

        @self.dp.callback_query_handler(lambda c: c.data.startswith('cat_'))
        async def process_category(call: types.CallbackQuery):
            await call.answer()
            cat = call.data.split('_')[1]
            tags = self.categories.get(
                random.choice(list(self.categories.keys())) if cat == "random" else self.categories.get(cat)
            
            if tags:
                await self.safe_send_image(call.from_user.id, tags)
            else:
                await call.message.answer("⚠️ Неизвестная категория")

    async def on_startup(self, dp):
        logger.info("Bot started")

    async def on_shutdown(self, dp):
        await self.session.close()
        logger.info("Bot stopped")

    def run(self):
        self.register_handlers()
        executor.start_polling(
            self.dp,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown,
            skip_updates=True,
            relax=0.5
        )

if __name__ == '__main__':
    bot = DanbooruBot()
    bot.run()
