"""用户管理单元测试"""
from web.app import UserManager


def test_password_is_hashed(tmp_path):
    """密码不以明文保存"""
    manager = UserManager(tmp_path / 'users.json')
    assert manager.add_user('alice', 'secret123')

    stored = manager.users['alice']['password']
    assert stored.startswith('pbkdf2_sha256$')
    assert 'secret123' not in stored
    assert manager.authenticate('alice', 'secret123')
    assert not manager.authenticate('alice', 'wrong')


def test_legacy_plaintext_password_is_upgraded(tmp_path):
    """旧的明文密码可登录，并在登录后升级为哈希"""
    from datetime import datetime

    manager = UserManager(tmp_path / 'users.json')
    manager.users['legacy'] = {'password': 'oldpass',
                               'created_at': datetime.now(),
                               'last_login': None}

    assert manager.authenticate('legacy', 'oldpass')
    assert manager.users['legacy']['password'].startswith('pbkdf2_sha256$')


def test_users_persist_and_reload(tmp_path):
    """用户写入文件后可重新加载"""
    path = tmp_path / 'users.json'
    manager = UserManager(path)
    manager.add_user('bob', 'bobpass123')

    reloaded = UserManager(path)
    assert reloaded.load()
    assert reloaded.authenticate('bob', 'bobpass123')

    assert 'bobpass123' not in path.read_text(encoding='utf-8')


def test_max_users_limits_accounts(tmp_path):
    """超过上限时无法继续添加"""
    manager = UserManager(tmp_path / 'users.json')
    manager.set_max_users(2)
    assert manager.add_user('u1', 'password1')
    assert manager.add_user('u2', 'password2')
    assert not manager.add_user('u3', 'password3')


def test_remove_user_clears_sessions(tmp_path):
    """删除用户同时清理其会话"""
    manager = UserManager(tmp_path / 'users.json')
    manager.add_user('carol', 'carolpass')
    manager.login('carol', 'session-1')

    assert manager.remove_user('carol')
    assert 'carol' not in manager.users
    assert 'session-1' not in manager.active_sessions
    assert not manager.remove_user('carol')


def test_list_users_hides_password(tmp_path):
    """用户列表不包含密码字段"""
    manager = UserManager(tmp_path / 'users.json')
    manager.add_user('dave', 'davepass')
    users = manager.list_users()

    assert users[0]['username'] == 'dave'
    assert 'password' not in users[0]
