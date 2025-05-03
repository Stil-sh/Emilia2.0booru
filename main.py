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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DanbooruBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.session = aiohttp.ClientSession()
        self.base_url = "https://danbooru.donmai.us"
        
        # SFW-категории с базовыми тегами
        self.categories = {
            "waifu": ["1girl", "solo", "cute"],
            "neko": ["cat_ears", "1girl"],
            "nature": ["landscape", "sky"],
            "food": ["food", "delicious"]
        }

    async def safe_fetch(self, url, params):
        """Безопасный запрос с повторными попытками"""
        for attempt in range(3):
            try:
                async with self.session.get(
                    url,
                    params=params,
                    timeout=10
                ) as resp:
                    if resp.status == 429:
                        delay = int(resp.headers.get('Retry-After', 30))
                        await asyncio.sleep(delay)
                        continue
                        
                    if resp.status != 200:
                        logger.error(f"HTTP Error {resp.status}")
                        return None
                        
                    return await resp.json()
                    
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(5)
                
        return None

    async def get_safe_post(self, tags):
        """Получение только SFW-контента"""
        params = {
            "tags": " ".join(tags + ["rating:general"]),
            "random": "true",
            "limit": 1
        }
        
        if DANBOORU_API_KEY and DANBOORU_USER:
            params.update({
                "login": DANBOORU_USER,
                "api_key": DANBOORU_API_KEY
            })
        
        data = await self.safe_fetch(f"{self.base_url}/posts.json", params)
        if not data or not isinstance(data, list):
            return None
            
        post = data[0]
        if not post.get('file_url') or post.get('rating') != 'g':
            return None
            
        # Обработка относительных URL
        image_url = post['file_url']
        if not image_url.startswith(('http://', 'https://')):
            image_url = f"{self.base_url}{image_url}"
            
        return image_url

    def create_keyboard(self):
        """Генерация интерактивной клавиатуры"""
        kb = InlineKeyboardMarkup(row_width=2)
        for category in self.categories:
            kb.insert(InlineKeyboardButton(
                category.capitalize(),
                callback_data=f"cat_{category}"
            ))
        kb.add(InlineKeyboardButton("🎲 Случайное", callback_data="cat_random"))
        return kb

    async def send_result(self, chat_id, tags):
        """Безопасная отправка результата"""
        try:
            image_url = await self.get_safe_post(tags)
            if not image_url:
                await self.bot.send_message(
                    chat_id,
                    "🔍 Не найдено подходящих изображений",
                    reply_markup=self.create_keyboard()
                )
                return
                
            await self.bot.send_photo(
                chat_id,
                image_url,
                reply_markup=self.create_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Send error: {str(e)}")
            await self.bot.send_message(
                chat_id,
                "⚠️ Произошла ошибка при загрузке",
                reply_markup=self.create_keyboard()
            )

    def setup_handlers(self):
        """Регистрация обработчиков"""
        @self.dp.message_handler(commands=['start', 'menu'])
        async def cmd_start(message: types.Message):
            await message.answer(
                "🌸 SFW Danbooru Бот\nВыберите категорию:",
                reply_markup=self.create_keyboard()
            )

        @self.dp.callback_query_handler(lambda c: c.data.startswith('cat_'))
        async def handle_category(call: types.CallbackQuery):
            await call.answer()
            category = call.data.split('_')[1]
            tags = self.categories.get(
                random.choice(list(self.categories.keys())) 
                if category == "random" 
                else self.categories.get(category)
            
            if tags:
                await self.send_result(call.from_user.id, tags)

    async def on_startup(self, dp):
        logger.info("====== Bot Started ======")

    async def on_shutdown(self, dp):
        await self.session.close()
        logger.info("====== Bot Stopped ======")

    def run(self):
        self.setup_handlers()
        executor.start_polling(
            self.dp,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown,
            skip_updates=True,
            relax=1,
            timeout=30
        )

if __name__ == '__main__':
    bot = DanbooruBot()
    bot.run()
