import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup
import logging
import os
import shelve

# Configure logging
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ['TOKEN']
CHANNEL_ID = 1194020361784795227  # Replace with your channel ID

URLs = [
    'https://dreamworldsilkroad.com/guild/_unitedbroz_',
    'https://dreamworldsilkroad.com/guild/unitedbroz',
]

# Configuration for scheduling interval
time_unit = 'seconds'
time_value = 10  # 10 seconds

intents = discord.Intents.default()
client = discord.Client(intents=intents)

HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

MAX_MESSAGE_LENGTH = 2000  # Maximum length for a Discord message


def send_message_in_chunks(channel, message):
  """Send a message in chunks if it exceeds the Discord limit."""
  for chunk in [
      message[i:i + MAX_MESSAGE_LENGTH]
      for i in range(0, len(message), MAX_MESSAGE_LENGTH)
  ]:
    client.loop.create_task(channel.send(chunk))


def fetch_data_from_website(url):
  try:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    rows = soup.select('#guildTable tbody tr')
    data = []
    for row in rows:
      cells = row.select('td')
      if len(cells) >= 5:
        character_name = cells[0].select_one(
            'a').text.strip() if cells[0].select_one('a') else 'N/A'
        level = cells[1].text.strip() if cells[1] else 'N/A'
        item_point = cells[4].text.strip() if len(cells) > 4 else 'N/A'
        character_data = {
            'name': character_name,
            'level': level,
            'item_points': item_point
        }
        data.append(character_data)
      else:
        logging.warning("Skipped a row due to missing data elements.")
    return data
  except requests.RequestException as e:
    logging.error(f"Failed to fetch data from {url}. Error: {e}")
    return []


def format_to_excel_table(data):
  formatted_message = "```python\n"
  formatted_message += "{:<2} | {:<12} | {:<6} | {:<6} | {:<2}\n".format(
      'No.', 'Name', 'Level', 'Item Points', 'Old No.')
  formatted_message += "-" * 80 + "\n"

  for idx, character in enumerate(data, start=1):
    formatted_message += "{:<2} | {:<12} | {:<6} | {:<6} | {:<2}\n".format(
        idx, f"{character['name']}", character['level'],
        character['item_points'], character.get('number', 'N/A'))

  formatted_message += "```"
  return formatted_message


def fetch_and_post_all_data():
  combined_data = []
  for url in URLs:
    combined_data.extend(fetch_data_from_website(url))

  sorted_combined_data = sorted(combined_data,
                                key=lambda x: int(x['item_points']),
                                reverse=True)

  for idx, char in enumerate(sorted_combined_data, start=1):
    char['number'] = idx

  if sorted_combined_data:
    message = format_to_excel_table(sorted_combined_data)
    channel = client.get_channel(CHANNEL_ID)

    if len(message) <= MAX_MESSAGE_LENGTH:
      client.loop.create_task(channel.send(message))
    else:
      send_message_in_chunks(channel, message)
  else:
    logging.warning("No data fetched from any URLs.")


@client.event
async def on_ready():
  logging.info(f'Logged in as {client.user.name}')
  if time_unit == 'seconds':
    fetch_data_task.start()
  elif time_unit == 'minutes':
    fetch_data_task.start()
  elif time_unit == 'hours':
    fetch_data_task.start()
  else:
    logging.error("Invalid time unit specified.")
    return


@tasks.loop(seconds=time_value)
async def fetch_data_task():
  fetch_and_post_all_data()


client.run(TOKEN)
