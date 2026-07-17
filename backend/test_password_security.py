import sys
from app.core.security import hash_password, verify_password

def run_tests():
    password = 'SuperSecretPassword123!'
    print('Running password security tests...')
    
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2, 'Hashes must be uniquely salted'
    print('? Hashing produces unique salts for the same password')
    
    assert verify_password(password, hash1) is True, 'Should verify valid password'
    assert verify_password(password, hash2) is True, 'Should verify valid password'
    print('? verify_password returns True for valid passwords')
    
    assert verify_password('WrongPassword123!', hash1) is False, 'Should reject wrong password'
    print('? verify_password returns False for incorrect passwords')
    
    assert verify_password(password, 'not-a-valid-bcrypt-hash') is False, 'Should safely handle malformed hash'
    assert verify_password(password, '') is False, 'Should safely handle empty hash'
    assert verify_password(password, None) is False, 'Should safely handle None hash'
    print('? verify_password safely handles malformed or invalid hashes')
    
    print('\nAll tests passed successfully!')

if __name__ == '__main__':
    try:
        run_tests()
    except AssertionError as e:
        print(f'? Test Failed: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'? Unexpected Error: {e}')
        sys.exit(1)
