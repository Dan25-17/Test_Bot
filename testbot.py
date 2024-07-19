import logging
import os
import json
import requests
import datetime
import pytz
from datetime import datetime as dt
from datetime import date, timedelta
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters, Updater, ConversationHandler, MessageHandler
from dotenv import load_dotenv

load_dotenv()


TIME, TIME_ONCE, DAYS, DAYS_ONCE, PERSON_ID, PERSON_ID_ONCE, WHO, TASK, TASK_ONCE = range(9)
ASKING_QUESTION, ASKING_WRONG, GETTING_WRONG = range(3)
ASKING_DUBBLE, GETTING_DUBBLE = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

secret_token = os.getenv('TOKEN')
admins = list(map(int, os.getenv('ADMIN').split(',')))
# student = os.getenv('STUDENT')
bot = os.getenv('BOT_USERNAME')
bot_password = os.getenv('BOT_PASSWORD')
admin_keyboard = ReplyKeyboardMarkup([['/set'],
                                      ['/set_once'],
                                      ['/unset'],
                                      ['/id_list'],
                                      ['/cancel'],
                                      ['/jobs']], 
                                      resize_keyboard=True)
remove_keyboard = ReplyKeyboardRemove()

host = os.getenv('BACKEND_HOST')

URL = host + '/api/questions/free_for_student/'
URL2 = host + '/api/questions/wrong/'
URL3 = host + '/api/questions/dubbles/'
URL4 = host + '/api/questions/'
URL_LOGIN = host + '/api/auth/jwt/create/'
URL_STUDENTS_LIST = host + '/api/students/'
URL1 = 'https://api.thecatapi.com/v1/images/search'


# getting token for api
response = requests.post(URL_LOGIN, json={'username': bot, 'password': bot_password})
backend_token = response.json()['access']

time_before_dubbles = 1



async def start_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ для ученика"""
    await update.message.reply_text("Привет! Я буду высылать тебе тесты!")


async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ для админа"""
    await update.message.reply_text("Привет! Я помогу настроить рассылку!", reply_markup=admin_keyboard)



async def jobs_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.jobs()
    await update.message.reply_text("Список текущих рассылок: id ученика_номер задания ЕГЭ, время рассылки")
    for job in jobs:
        await update.message.reply_text(f"{job.name} {job.trigger}")

def students_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /students_id 1 - один студент
    # /students_id - все студенты
    user = update.effective_message.chat_id
    try:
        if context.args:
            
            response = requests.get(f'{URL_STUDENTS_LIST}{context.args[0]}', headers={'Authorization': f'Bearer {backend_token}'})
            students = response.json()
            name = students['first_name']
            surname = students['last_name']
            tg_id = students['tg_id']
            message = f'{name} {surname} \n {tg_id}'
        else:
            response = requests.get(URL_STUDENTS_LIST, headers={'Authorization': f'Bearer {backend_token}'})
            message = ''
            students = response.json()
            for student in students:
                name = student['first_name']
                surname = student['last_name']
                tg_id = student['tg_id']
                message += f'{name} {surname} \n {tg_id} \n\n'

    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        new_url = 'https://api.thecatapi.com/v1/images/search'
        response = requests.get(new_url)
        message = response.json()
    return context.bot.send_message(user, message, )


async def set_tests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите время отправки теста в формате ЧЧ:ММ")
    # await update.message.reply_video('https://www.youtube.com/embed/watch?v=dQw4w9WgXcQ')
    return TIME


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_time'] = message
    await update.message.reply_text("Теперь введите дни от 0 (воскресенье) до 6 (суббота) через пробел")
    return DAYS


async def set_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_days'] = message
    await update.message.reply_text("Теперь введите id ученика")
    return PERSON_ID


async def set_person_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_person'] = message
    await update.message.reply_text("Теперь введите номер задания ЕГЭ для ученика")
    return TASK

async def set_tests_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите время отправки теста в формате ЧЧ:ММ")
    return TIME_ONCE

async def set_time_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_time_once'] = message
    await update.message.reply_text("Теперь введите дату в формате 'год, месяц, день'")
    print(message)
    return DAYS_ONCE


async def set_days_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_days_once'] = message
    await update.message.reply_text("Теперь введите id ученика")
    print(message)
    return PERSON_ID_ONCE


async def set_person_id_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['job_person'] = message
    await update.message.reply_text("Теперь введите номер задания ЕГЭ для ученика")
    print(message)
    return TASK_ONCE


async def set_task_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    print(message)
    context.user_data['task'] = message

    try:
        tz = pytz.timezone('Europe/Moscow')
        time = dt.strptime(context.user_data['job_time_once'], '%H:%M').time().replace(tzinfo=tz)
        print(time)
        d = list(map(int, context.user_data['job_days_once'].split(', ')))
        days = date(*d)
        print(days)
        when = datetime.datetime.combine(days, time)
        print(when)
        student_id = int(context.user_data['job_person'])
        task = int(context.user_data['task'])
        chat_id = update.effective_message.chat_id
        print(345556)

        context.job_queue.run_once(request_test_start,
                                    when=time,
                                    chat_id=chat_id,
                                    user_id=student_id,
                                    name=f'{student_id}_{task}',
                                    data={
                                        'student_id': student_id,
                                        'task': task,
                                        'dubbles': False
                                    })
        print(context.job_queue.get_jobs_by_name(f'{student_id}_{task}'))
        await update.message.reply_text("Готово")
    except:
        await update.message.reply_text("Что-то не то с данными")
    return ConversationHandler.END


async def set_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['task'] = message

    try:
        tz = pytz.timezone('Europe/Moscow')
        # needed_time = datetime.time(00, 00, 00, 000000, tz)
        # days = (1, 2, 3, 4, 5, 6, 0,)
        time_input = dt.strptime(context.user_data['job_time'], '%H:%M').time().replace(tzinfo=tz)
        days = (int(i) for i in (context.user_data['job_days']).split())
        student_id = int(context.user_data['job_person'])
        task = int(context.user_data['task'])
        chat_id = update.effective_message.chat_id

        context.job_queue.run_daily(request_test_start,
                                    time=time_input,
                                    days=days,
                                    chat_id=chat_id,
                                    user_id=student_id,
                                    name=f'{student_id}_{task}',
                                    data={
                                        'student_id': student_id,
                                        'task': task,
                                        'dubbles': False
                                    })
        print(context.job_queue.get_jobs_by_name(str(student_id)))
        await update.message.reply_text("Готово")
    except:
        await update.message.reply_text("Что-то не то с данными")
    return ConversationHandler.END



async def cancel_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    await update.message.reply_text("Отмена")
    return ConversationHandler.END


def message_question(context):
    cur = context.user_data['current_question']
    cur_q = context.user_data['questions'][cur]
    name = cur_q['name']
    task = cur_q['task']
    message = f'*{name}* \n {task}'
    return message


async def request_test_start(context: ContextTypes.DEFAULT_TYPE):
    keyboard1 = ReplyKeyboardMarkup([['/start_test']], resize_keyboard=True, one_time_keyboard=True)
    keyboard2 = ReplyKeyboardMarkup([['/start_dubbles']], resize_keyboard=True, one_time_keyboard=True)
    job_name = context.job.name
    dubbles = context.job.data['dubbles']
    student_id, task = job_name.split('_')
    if not dubbles:
        await context.bot.send_message(int(student_id),
                                        'Готовы начать сегодняшнее тестирование? Нажмите кнопку "start_test", чтобы начать! Ответы вводятся без пробелов.',
                                        reply_markup=keyboard1)
    else:
        await context.bot.send_message(int(student_id),
                                        'Готовы начать повторенире ошибок? Нажмите на кнопку ниже!',
                                        reply_markup=keyboard2)


async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = context.user_data['task']
    response = requests.get(URL + f'?task={task}&user={update.effective_message.chat_id}', headers={'Authorization': f'Bearer {backend_token}'})

    context.user_data['questions'] = response.json()
    context.user_data['current_question'] = 0
    message = message_question(context)
    await update.message.reply_text(message, reply_markup=remove_keyboard, parse_mode='Markdown')
    return ASKING_QUESTION


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    cur = context.user_data['current_question']
    q = context.user_data['questions'][cur]
    user = update.effective_message.chat_id

    response = requests.post(
        URL4 + f'{q["order"]}/student_answer/',
        headers={'Authorization': f'Bearer {backend_token}'},
        data={
            'user': user,
            'answer': message
        }
    )
    response = response.json()
    if response['answer'] == 'wrong':
        explanation = response['explanation']
        await update.message.reply_text('Что-то не так, посмотрите, как стоило сделать:')
        await update.message.reply_text(explanation)


    context.user_data['current_question'] += 1
    if context.user_data['current_question'] == len(context.user_data['questions']):

        await update.message.reply_text('Тест завершен, давайте посмотрим на ваши результаты')

        task = context.user_data['task']
        response = requests.get(
            URL2 + f'?task={task}&user={update.effective_message.chat_id}',
            headers={'Authorization': f'Bearer {backend_token}'}
        )
        if response.json():
            context.user_data['questions'] = response.json()
            context.user_data['current_question'] = 0
            message = message_question(context)
            await update.message.reply_text(message, reply_markup=remove_keyboard)
            return ASKING_WRONG
        else:
            return ConversationHandler.END

    message = message_question(context)
    await update.message.reply_text(message)
    return ASKING_QUESTION 

async def ask_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    cur = context.user_data['current_question']
    q = context.user_data['questions'][cur]
    user = update.effective_message.chat_id

    response = requests.post(
        URL4 + f'{q["order"]}/student_answer/',
        headers={'Authorization': f'Bearer {backend_token}'},
        data={
            'user': user,
            'answer': message
        }
    )
    response = response.json()
    if response['answer'] == 'wrong':
        explanation = response['explanation']
        await update.message.reply_text('Что-то не так, посмотрите, как стоило сделать:')
        await update.message.reply_text(explanation)

    context.user_data['current_question'] += 1
    if context.user_data['current_question'] == len(context.user_data['questions']):
        await update.message.reply_text('Тест завершен')
        task = context.user_data['task']
        context.job_queue.run_once(request_test_start,
                                    when=timedelta(hours=24),
                                    chat_id=user,
                                    user_id=user,
                                    name=f'{user}_{task}',
                                    data={
                                        'student_id': user,
                                        'task': task,
                                        'dubbles': True
                                    })

        return ConversationHandler.END

    message = message_question(context)
    await update.message.reply_text(message, reply_markup=remove_keyboard, parse_mode='Markdown')
    return ASKING_WRONG 




async def start_dubbles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = context.user_data['task']
    response = requests.get(URL3 + f'?task={task}&user={update.effective_message.chat_id}', headers={'Authorization': f'Bearer {backend_token}'})
    
    context.user_data['questions'] = response.json()
    context.user_data['current_question'] = 0
    message = message_question(context)
    await update.message.reply_text(message, reply_markup=remove_keyboard, parse_mode='Markdown')
    return ASKING_DUBBLE


async def ask_dubble(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    cur = context.user_data['current_question']
    q = context.user_data['questions'][cur]
    user = update.effective_message.chat_id

    response = requests.post(
        URL4 + f'{q["order"]}/student_answer/',
        headers={'Authorization': f'Bearer {backend_token}'},
        data={
            'user': user,
            'answer': message
        }
    )
    response = response.json()
    if response['answer'] == 'wrong':
        explanation = response['explanation']
        await update.message.reply_text('Что-то не так, посмотрите, как стоило сделать:')
        await update.message.reply_text(explanation)

    context.user_data['current_question'] += 1
    if context.user_data['current_question'] == len(context.user_data['questions']):

        await update.message.reply_text('Тест завершен')
        return ConversationHandler.END

    message = message_question(context)
    await update.message.reply_text(message)
    return ASKING_DUBBLE 

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Отмена запланированной рассылки заданий"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def choose_cancel_sending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jobs = context.job_queue.jobs()
    await update.message.reply_text("Список текущих рассылок")
    for job in jobs:
        await update.message.reply_text(f"{job.name} {job.trigger}")
    await update.message.reply_text("Введите название рассылки, которую надо удалить, в формате id_тема")
    return WHO

async def cancel_sending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена рассылки"""
    message = update.message.text
    job_removed = remove_job_if_exists(message, context)
    text = "Действие отменено." if job_removed else "Для данного name нет подготовленных тестов"
    await update.message.reply_text(text)
    return ConversationHandler.END


def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(secret_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "help"], start_student))
    application.add_handler(CommandHandler("admin", start_admin, filters=filters.User(admins)))
    application.add_handler(CommandHandler("jobs", jobs_list, filters=filters.User(admins)))

    unset_handler = ConversationHandler(
        entry_points=[CommandHandler("unset", choose_cancel_sending, filters=filters.User(admins))],
        states={
            WHO: [MessageHandler(filters.TEXT, cancel_sending)],
        },
        fallbacks=[CommandHandler("cancel", cancel_set, filters=filters.User(admins))],
    )

    set_handler = ConversationHandler(
        entry_points=[CommandHandler("set", set_tests, filters=filters.User(admins))],
        states={
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_days)],
            PERSON_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_person_id)],
            TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_task)],
        },
        fallbacks=[CommandHandler("cancel", cancel_set, filters=filters.User(admins))],
    )

    set_once_handler = ConversationHandler(
        entry_points=[CommandHandler("set_once", set_tests_once, filters=filters.User(admins))],
        states={
            TIME_ONCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time_once)],
            DAYS_ONCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_days_once)],
            PERSON_ID_ONCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_person_id_once)],
            TASK_ONCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_task_once)],
        },
        fallbacks=[CommandHandler("cancel", cancel_set, filters=filters.User(admins))],
    )

    test_handler = ConversationHandler(
        entry_points=[CommandHandler("start_test", start_test)],
        states={
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question)],
            ASKING_WRONG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_wrong)]
        },
        fallbacks=[CommandHandler("cancel", cancel_set)],
    )

    test_dubbles_handler = ConversationHandler(
        entry_points=[CommandHandler("start_dubbles", start_dubbles)],
        states={
            ASKING_DUBBLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_dubble)],
        },
        fallbacks=[CommandHandler("cancel", cancel_set)],
    )



    students_list = (CommandHandler("id_list", students_id, filters=filters.User(admins)))

    application.add_handler(set_handler)
    application.add_handler(set_once_handler)
    application.add_handler(unset_handler)
    application.add_handler(test_handler)
    application.add_handler(test_dubbles_handler)
    application.add_handler(students_list)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()