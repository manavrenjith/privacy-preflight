// Test fixture: Authentication module using Argon2id password hashing baseline
// Note: Code text fixture for testing and demonstration only; not executed.
// Addresses IN-BP-003 and IN-DPDP-013.
const argon2 = require('argon2');

/**
 * Hashes a user password using argon2id with recommended baseline parameters.
 * @param {string} password - The plaintext password to hash.
 * @returns {Promise<string>} The argon2id password hash.
 */
async function hashPassword(password) {
  return await argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: 65536, // 64 MB
    timeCost: 3,       // 3 iterations
    parallelism: 4
  });
}

/**
 * Verifies a password against an argon2id hash.
 * @param {string} storedHash - The stored argon2id hash.
 * @param {string} password - The plaintext candidate password.
 * @returns {Promise<boolean>} True if password matches.
 */
async function verifyPassword(storedHash, password) {
  return await argon2.verify(storedHash, password);
}

module.exports = { hashPassword, verifyPassword };

