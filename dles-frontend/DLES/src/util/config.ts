// 后端地址，可通过 .env.local 里的 VITE_API_BASE_URL 修改。
// 登录状态保存在 SameSite=Lax 的 Cookie 里，前后端必须是同一个站点（域名相同，端口可以不同），
// 所以默认使用当前页面的主机名，这样用 localhost 或 127.0.0.1 打开前端都能正常登录。
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:8080`;

export const avatarUrl = (avatarPath: string) =>
  `${API_BASE_URL}/avatars/${encodeURIComponent(avatarPath)}`;
