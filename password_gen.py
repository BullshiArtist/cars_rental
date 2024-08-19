from werkzeug.security import generate_password_hash, check_password_hash

# Define the plain text password
password = '123456'

# Generate a password hash
hashed_password = generate_password_hash(password)

# Print the hashed password
print(f"this is :{hashed_password}")

#check the password
if check_password_hash(hashed_password, '123456'):
    print('Password is correct')
else:
    print('Password is incorrect')