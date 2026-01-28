/* 
 * 인증 관리 서비스
 * localStorage를 사용한 간단한 인증 시스템
 * 실제 users.json은 public/users.json에 위치
 */

const STORAGE_KEY = 'smart_cs_user';

export const login = async (username, password) => {
  try {
    const response = await fetch('/users.json');
    const data = await response.json();
    
    const user = data.users.find(
      u => u.username === username && u.password === password
    );
    
    if (user) {
      const userInfo = { ...user };
      delete userInfo.password;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userInfo));
      return { success: true, user: userInfo };
    }
    
    return { success: false, message: '아이디 또는 비밀번호가 일치하지 않습니다.' };
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, message: '로그인 중 오류가 발생했습니다.' };
  }
};

export const logout = () => {
  localStorage.removeItem(STORAGE_KEY);
};

export const getCurrentUser = () => {
  const userStr = localStorage.getItem(STORAGE_KEY);
  return userStr ? JSON.parse(userStr) : null;
};

export const isAuthenticated = () => {
  return getCurrentUser() !== null;
};
