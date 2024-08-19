import base64

path = '/home/calvin/PycharmProjects/cars rent/static/images/2022-toyota-rav4-cavalry-blue.jpg'

# Open image file in binary mode
with open(path, 'rb') as image_file:
    # Convert to base64
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

# Print the encoded string (this will be used in the SQL file)
print(encoded_string)