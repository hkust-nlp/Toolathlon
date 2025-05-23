const { chromium } = require('playwright');

(async () => {
  console.log('正在启动浏览器...');
  const browser = await chromium.launch();
  console.log('浏览器已成功启动');
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 记录开始时间
  console.log('开始导航到 example.com...');
  const startTime = Date.now();
  
  try {
    console.error(page)
    await page.goto('https://example.com', { waitUntil: 'domcontentloaded' });
    
    // 计算并输出导航耗时
    const endTime = Date.now();
    const duration = endTime - startTime;
    console.log(`导航完成，耗时 ${duration} 毫秒`);
    
    await page.screenshot({ path: 'screenshot.png' });
  } catch (error) {
    // 如果导航出错，也记录耗时
    const errorTime = Date.now();
    const duration = errorTime - startTime;
    console.error(`导航失败，耗时 ${duration} 毫秒`);
    console.error('错误详情:', error);
    throw error; // 重新抛出错误，让外面的 catch 捕获
  }
  
  await browser.close();
})().catch(error => {
  console.error('运行出错:', error);
  process.exit(1);
});