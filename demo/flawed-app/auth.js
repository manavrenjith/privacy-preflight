// Test fixture: Insecure authentication module using MD5 password hashing
// Planted flaw for IN-BP-003 / IN-DPDP-013. Not for production use.
const crypto = require('crypto');

function hashPassword(password) {
  // Insecure: MD5 is vulnerable to collision attacks and lacks work-factor adaptation
  return crypto.createHash('md5').update(password).digest('hex');
}

function verifyPassword(storedHash, password) {
  const hash = crypto.createHash('md5').update(password).digest('hex');
  return storedHash === hash;
}

module.exports = { hashPassword, verifyPassword };

