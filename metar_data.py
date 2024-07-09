import tkinter as tk
import requests
import math
from urllib.parse import urlencode
import fractions 




# Constants
METAR_URL = "https://aviationweather.gov/cgi-bin/data/metar.php??ids=KTYS&format=raw&date=&hours=0"
METAR_PARAMS = {"ids": "KTYS", "format": "raw", "date": "", "hours": 0}


def fetch_metar_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch METAR data: {e}")
        return None


def extract_first_word_from_line(line):
    words = line.split()
    return words[0] if words else None


def extract_second_word_from_line(line):
    words = line.split()
    if len(words) > 1:
        second_word = words[1]
        if not second_word.endswith('Z'):
            for word in words[2:]:
                if word.endswith('Z') and word[0].isdigit():
                    return word[:2], word[2:-1]
            return None, None
        return second_word[:2], second_word[2:-1]
    else:
        return None, None






def extract_wind_from_line(line):
  words = line.split()
  for i, word in enumerate(words):
      if word.endswith('KT'):
          wind_info = word
          gust_index = wind_info.find('G')
          vrb_index = wind_info.find('V')


          if 'G' in wind_info and gust_index != -1 and gust_index + 2 < len(wind_info):
              return wind_info[:gust_index], wind_info[gust_index + 1:-2], vrb_index
          elif 'V' in wind_info and vrb_index != -1 and vrb_index + 4 < len(wind_info):
              return wind_info[:vrb_index], wind_info[vrb_index + 1:-2], vrb_index
          else:
              return wind_info, None, None
  return None, None, None




def extract_visibility_from_line(line):
  words = line.split()
  for word in words[3:]:
      if word.endswith('SM'):
          return word[:-2]
  return None




def extract_degree_dewpoint_from_line(line):
  # Split the line by spaces and extract the temperature and dewpoint information
  words = line.split()
  for word in words[4:]:
      if '/' in word and 'SM' not in word:
          slash_index = word.index('/')
          degree = word[:slash_index]
          dewpoint = word[slash_index + 1:]


          # Check for 'M' in degree and dewpoint
          if 'M' in degree:
              degree = f"-{degree[1:]}"  # Exclude 'M' and store as a negative value
          if 'M' in dewpoint:
              dewpoint = f"-{dewpoint[1:]}"  # Exclude 'M' and store as a negative value


          # Remove leading zeros
          degree = degree.lstrip("0") or "0"
          dewpoint = dewpoint.lstrip("0") or "0"


          return {'degree': degree, 'dewpoint': dewpoint}
  return None






def extract_altimeter_from_line(line):
  words = line.split()
  for word in words[5:]:
      if word.startswith('A') and word[1:].isdigit() and len(word) == 5:
          altimeter_value = f"{word[1:3]}.{word[3:]}"
          return {'altimeter': altimeter_value}
  return None




def convert_to_numeric(s):
  try:
      if s is None:
          return None
      # Check if s is already a numeric value
      if isinstance(s, (int, float, fractions.Fraction)):  # Fix this line
          return s
      numeric_part = ''.join(c for c in str(s) if c.isdigit() or c in [' ', '/', '.'])
      result = eval(numeric_part.replace(' ', '+'))
      if isinstance(result, fractions.Fraction):
          result = float(result)
      return result
  except (ValueError, ZeroDivisionError, SyntaxError) as e:
      print(f"Error converting '{s}' to a numeric value: {e}")
      return None






def convert_utc_to_12_hour_clock(utc_time, timezone_offset):
  # Convert UTC time to 12-hour clock format with timezone offset
  hours = int(utc_time[:2])
  suffix = 'AM' if hours < 12 else 'PM'


  # Adjust hours based on timezone offset
  hours = (hours + timezone_offset) % 12 or 12


  return f"{hours:02d}:{utc_time[2:4]} {suffix}"














def create_airport_dict(metar_data):
  airport_dict = {}


  for line in metar_data.split('\n'):
      first_word = extract_first_word_from_line(line)
      second_word_prefix, second_word_suffix = extract_second_word_from_line(line)
      wind_info, wind_gust, vrb_index = extract_wind_from_line(line)
      visibility_info = extract_visibility_from_line(line)
      degree_dewpoint_info = extract_degree_dewpoint_from_line(line)
      altimeter_info = extract_altimeter_from_line(line)


      if first_word:
          if wind_info:
              wind_dir = wind_info[:3] if vrb_index is None else 'VRB'  # Default to VRB if variable
              wind_speed = wind_info[3:5]
              airport_dict[first_word] = {
                  'date': second_word_prefix,
                  'utc': second_word_suffix,
                  'wind_dir': wind_dir,
                  'wind_speed': wind_speed,
                  'wind_gust': wind_gust  # Add wind gust information
              }
          else:
              airport_dict[first_word] = {
                  'date': second_word_prefix,
                  'utc': second_word_suffix
              }


          visibility_info = extract_visibility_from_line(line)
          degree_dewpoint_info = extract_degree_dewpoint_from_line(line)
          altimeter_info = extract_altimeter_from_line(line)


          if visibility_info:
              vis = convert_to_numeric(visibility_info)
              # Check for conditions related to visibility
              if vis is not None:
                  airport_dict[first_word]['vis'] = vis
                  if vis < 1.0:
                      print(f"Low visibility at {first_word}: {vis} miles")


          if degree_dewpoint_info:
              airport_dict[first_word].update(degree_dewpoint_info)
              if 'degree' not in airport_dict[first_word]:
                  airport_dict[first_word]['degree'] = 0
              if 'dewpoint' not in airport_dict[first_word]:
                  airport_dict[first_word]['dewpoint'] = 0


          if altimeter_info:
              # Check for conditions related to altimeter
              airport_dict[first_word].update(altimeter_info)
              altimeter_value = convert_to_numeric(altimeter_info['altimeter'])
              if altimeter_value is not None and altimeter_value < 29.8:
                  print(f"Low pressure at {first_word}: Altimeter setting {altimeter_value} inHg")


  return airport_dict














def parse_metar(metar_line):
    return create_airport_dict(metar_line)




def parse_metar_data(metar_data):
    parsed_data = create_airport_dict(metar_data)
    choices = list(parsed_data.keys())
    return choices, parsed_data




def convert_knots_to_mph(knots):
  # Convert wind speed from knots to miles per hour
  knots_numeric = convert_to_numeric(knots)
  if knots_numeric is not None:
      return int(knots_numeric * 1.15)
  return 0 






def convert_celsius_to_fahrenheit(celsius):
  # Convert temperature and dewpoint from Celsius to Fahrenheit
  celsius_numeric = convert_to_numeric(celsius)
  if celsius_numeric is not None:
      return int(celsius_numeric * 9/5 + 32)
  return 0




def convert_utc_to_am_pm_format(utc_time, timezone_offset):
    # Convert UTC time to 12-hour clock format with timezone offset
    hours = int(utc_time[:2]) + timezone_offset
    suffix = 'am' if 0 <= hours < 12 else 'pm'
    hours = hours % 12 or 12
    return f"{hours:02d}{utc_time[2:4]}{suffix}"




def draw_temperature_gauge(canvas, temperature, dewpoint):
    # Check if temperature is a string or numeric
    if isinstance(temperature, str):
        temperature_f = convert_celsius_to_fahrenheit(temperature)
    elif isinstance(temperature, (int, float)):
        temperature_f = int(temperature)
    else:
        temperature_f = 0  # Default value if conversion fails


    dewpoint_f = convert_celsius_to_fahrenheit(dewpoint)


    print(f"Temperature: {temperature}, Dewpoint: {dewpoint}")
    print(f"Converted Temperature: {temperature_f}°F, Converted Dewpoint: {dewpoint_f}°F")


    # Draw the temperature gauge on the canvas with a border
    canvas.create_rectangle(500, 100, 600, 300, outline="black", fill="white", width=5)
    canvas.create_rectangle(500, 200, 600, 300, outline="black", fill="blue", tags="temp_gauge")


    # Calculate the difference between temperature and dewpoint
    temperature_difference = max(temperature_f - dewpoint_f, 0)


    # Draw a red bar inside the blue box based on the temperature difference
    canvas.create_rectangle(500, 200, 600, 200 - temperature_difference, outline="black", fill="red", tags="temp_bar")


    # Draw temperature below the box in red
    canvas.create_text(550, 310, text=f"{temperature_f}°F", fill="red", tags="temp_text", font=("Helvetica", 12))


    # Draw dewpoint below the temperature in blue
    canvas.create_text(550, 330, text=f"{dewpoint_f}°F", fill="blue", tags="dewpoint_text", font=("Helvetica", 12))














def draw_wind_gauge(canvas, wind_dir, wind_speed, wind_gust):
  canvas.create_oval(300, 100, 400, 200, outline="black", fill="gray")


  if wind_dir.isdigit():  # Check if wind direction is numeric
      wind_dir_numeric = float(wind_dir)
      canvas.create_line(350, 150, 350 + 50 * math.cos(math.radians(360 - wind_dir_numeric)),
                         150 - 50 * math.sin(math.radians(360 - wind_dir_numeric)), fill="black", width=2)
  elif wind_dir == 'VRB':  # Handle variable wind direction
      canvas.create_text(350, 150, text="VRB", fill="black", tags="wind_text")
  elif wind_dir == '000':  # Handle calm winds
      canvas.create_text(350, 150, text="Calm", fill="black", tags="wind_text")
  else:
      print(f"Invalid wind direction: {wind_dir}")


  # Move the wind speed and gust text below the circle
  if wind_speed == '0':  # Check if wind speed is calm
      canvas.create_text(350, 210, text="Calm", fill="green", tags="wind_text")
  else:
      canvas.create_text(350, 210, text=f"{convert_knots_to_mph(wind_speed)} MPH", fill="black",
                         tags="wind_text")
      canvas.create_text(350, 240, text=f"Gust: {convert_knots_to_mph(wind_gust)} MPH", fill="red", tags="wind_text")


  # Draw a smaller red circle inside the main circle
  canvas.create_oval(345, 145, 355, 155, outline="red", fill="red")


















def draw_visibility_gauge(canvas, visibility):
  visibility_ratio = visibility / 10.0
  orange_width = 400 * visibility_ratio
  gray_width = 400 - orange_width


  # Draw the bold border around the entire gauge
  canvas.create_rectangle(300, 400, 700, 500, outline="black", width=5)  # Bold border


  # Draw the orange and gray rectangles for the gauge
  canvas.create_rectangle(300, 400, 300 + orange_width, 500, outline="black", fill="orange", tags="vis_gauge")
  canvas.create_rectangle(300 + orange_width, 400, 700, 500, outline="black", fill="gray", tags="vis_gauge")


  # Draw the visibility text outside the box in the lower-left corner
  canvas.create_text(300, 520, text=f"{visibility} SM", fill="green", anchor="w", font=("Helvetica", 12), tags="vis_text")










def draw_altimeter_gauge(canvas, altimeter_value):
  canvas.create_oval(300, 250, 400, 350, outline="black", fill="black")  # Black circle
  canvas.create_text(350, 300, text=f"{altimeter_value}", fill="white", tags="altimeter_text", font=("Helvetica", 12))






def run(metar_data):
    # Parse metar_data to extract relevant information and populate the choices list
    choices, airport_data = parse_metar_data(metar_data)


    # Create the root Tk()
    root = tk.Tk()
    # Set the title
    root.title("COSC505 - Weather")
    # Create two frames, the list is on top of the Canvas
    list_frame = tk.Frame(root)
    draw_frame = tk.Frame(root)
    # Set the list grid in c,r = 0,0
    list_frame.grid(column=0, row=0)
    # Set the draw grid in c,r = 0,1
    draw_frame.grid(column=0, row=1)


    # Create the canvas on the draw frame, set the width to 800 and height to 600
    canvas = tk.Canvas(draw_frame, width=800, height=600)
    # Reset the size of the grid
    canvas.pack()


    # Create a variable that will store the currently selected choice.
    listvar = tk.StringVar(root)
    # Immediately set the choice to the first element. Double-check to make sure choices[0] is valid!
    listvar.set(choices[0])


    dropdown = tk.OptionMenu(list_frame, listvar, *choices)
    # The dropdown menu is on the top of the screen. This will make sure it is in the middle.
    dropdown.grid(row=0, column=1)


    def draw_widgets(selected_airport, timezone_offset):
      canvas.delete("all")  # Clear the canvas before redrawing
      canvas.create_text(100, 100, text=f"{listvar.get()}", fill="red", tags="airport_text", font=("Helvetica", 20))


      # Update time with timezone offset
      utc_time = selected_airport.get('utc', '')
      formatted_time = convert_utc_to_am_pm_format(utc_time, timezone_offset)
      canvas.create_text(100, 150, text=f"{formatted_time.lstrip('0').lower()}", fill="blue", tags="time_text", font=("Helvetica", 20))




      # Draw temperature gauge
      draw_temperature_gauge(canvas, selected_airport.get('degree', 0), selected_airport.get('dewpoint', 0))
      draw_altimeter_gauge(canvas, selected_airport.get('altimeter', 0))
      draw_wind_gauge(canvas, selected_airport.get('wind_dir', 0),
                      selected_airport.get('wind_speed', 0), selected_airport.get('wind_gust', 0))
      draw_visibility_gauge(canvas, selected_airport.get('vis', 0))


    # This function is called whenever the user selects another. Change this as you see fit.
    def drop_changed(*args):
      selected_airport = airport_data[listvar.get()]
      draw_widgets(selected_airport, timezone_offset = 5)


    # Listen for the dropdown to change. When it does, the function drop_changed is called.
    listvar.trace('w', drop_changed)
    # You need to draw the text manually with the first choice.
    drop_changed()


    # mainloop() is necessary for handling events
    tk.mainloop()


if __name__ == "__main__":
    metar_url = f"{METAR_URL}?{urlencode(METAR_PARAMS)}"
    metar_data = fetch_metar_data(metar_url)


    if metar_data:
      choices, airport_data = parse_metar_data(metar_data)
      run(metar_data)