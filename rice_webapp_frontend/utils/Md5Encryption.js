import md5 from 'md5';

export function Md5Encryption(payloadValue) {
  return md5(payloadValue);
}