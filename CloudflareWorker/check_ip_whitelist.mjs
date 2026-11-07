import { isIpWhitelisted, isOriginWhitelisted } from './src/security.ts';
import fs from 'fs';

const toml = fs.readFileSync('./wrangler.toml', 'utf8');
const ipMatch = toml.match(/ALLOWED_IPS\s*=\s*"([^"]+)"/);
const allowedIps = ipMatch ? ipMatch[1] : '';

console.log('=== BÁO CÁO KIỂM TRA IP WHITELIST ===\n');
console.log('1. Giá trị ALLOWED_IPS trong wrangler.toml:');
console.log('  ', allowedIps);

const testIp = '113.185.73.217';
const isAllowed = isIpWhitelisted(testIp, allowedIps);

console.log(`\n2. Kiểm tra IP: "${testIp}"`);
console.log('   Kết quả phân giải:', isAllowed ? '✅ ĐÃ ĐƯỢC WHITELIST (HỢP LỆ)' : '❌ BỊ TỪ CHỐI');

// Test cả khi ENFORCE_IP_WHITELIST = "true"
console.log('\n3. Kiểm tra khả năng gửi POST request khi bật ENFORCE_IP_WHITELIST = "true":');
if (isAllowed) {
  console.log('   ✅ ĐỦ ĐIỀU KIỆN: Request từ IP này sẽ vượt qua Security Gate an toàn.');
} else {
  console.log('   ❌ KHÔNG ĐỦ ĐIỀU KIỆN: Sẽ bị chặn 403 Forbidden.');
}

console.log('\n======================================');
