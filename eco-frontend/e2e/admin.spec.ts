import {test,expect} from '@playwright/test'

test('save waits for the API; create, update, dismiss and expiry work',async({page})=>{
 const sources:Record<string,unknown>[]=[]
 let release:()=>void=()=>{}
 const pending=new Promise<void>(resolve=>{release=resolve})
 await page.route('**/admin/benchmark/**',async route=>{
  const req=route.request()
  expect(req.headers().authorization).toBe('Bearer '+'x'.repeat(32))
  if(req.url().endsWith('/collect')||req.url().endsWith('/report')){
   await route.fulfill({json:{run_id:'test-run',counts:{PASS:1,REVIEW:1,REJECT:1},sources:[],records:[]}});return
  }
  if(req.method()==='POST'){await pending;sources.push(req.postDataJSON())}
  if(req.method()==='PUT')sources[0]=req.postDataJSON()
  if(req.method()==='DELETE'){sources.pop();await route.fulfill({status:204});return}
  await route.fulfill({status:req.method()==='POST'?201:200,json:req.method()==='GET'?{sources}:sources[0]})
 })
 await page.goto('/admin/benchmark')
 await page.getByLabel('Administrator token').fill('x'.repeat(32))
 await page.getByRole('button',{name:'Connect',exact:true}).click()
 await page.getByLabel('Source ID').fill('test')
 await page.getByLabel('Source URL').fill('https://www.cso.ie/data.csv')
 await page.getByLabel('Enable source').check()
 await page.getByRole('button',{name:'Save source',exact:true}).click()
 await expect(page.getByRole('button',{name:'Save source',exact:true})).toBeDisabled()
 await expect(page.locator('.success-toast')).toHaveCount(0)
 release()
 await expect(page.locator('.success-toast')).toContainText('Source "test" saved successfully.')
 await expect(page.getByRole('cell',{name:'Enabled',exact:true})).toBeVisible()
 await page.screenshot({path:'test-results/source-saved-mobile.png',fullPage:true})
 await page.getByRole('button',{name:'Dismiss success notification'}).click()
 await expect(page.locator('.success-toast')).toHaveCount(0)
 await page.getByRole('button',{name:'Edit / disable'}).click()
 await page.getByLabel('Enable source').uncheck()
 await page.getByRole('button',{name:'Save source',exact:true}).click()
 await expect(page.locator('.success-toast')).toContainText('updated successfully')
 await expect(page.getByRole('cell',{name:'Disabled',exact:true})).toBeVisible()
 await expect(page.locator('.success-toast')).toHaveCount(0,{timeout:8000})
 await page.getByRole('button',{name:'Run Collection',exact:true}).click()
 await expect(page.getByText('Run: test-run')).toBeVisible()
 page.on('dialog',dialog=>dialog.accept())
 await page.getByRole('button',{name:'Delete',exact:true}).click()
 await expect(page.getByText('No sources yet. Add a source to get started.')).toBeVisible()
 expect(await page.evaluate(()=>localStorage.length+sessionStorage.length)).toBe(0)
 await page.getByRole('button',{name:'Sign out and clear token'}).click()
 await expect(page.getByLabel('Administrator token')).toHaveValue('')
})

for(const failure of [401,409,422,503,'network'] as const){
 test(`failed save (${failure}) retains input and never shows success`,async({page})=>{
  await page.route('**/admin/benchmark/**',async route=>{
   if(route.request().method()==='GET'){await route.fulfill({json:{sources:[]}});return}
   if(failure==='network'){await route.abort('failed');return}
   await route.fulfill({status:failure,json:{detail:'Source could not be saved'}})
  })
  await page.goto('/admin/benchmark')
  await page.getByLabel('Administrator token').fill('x'.repeat(32))
  await page.getByRole('button',{name:'Connect',exact:true}).click()
  await page.getByLabel('Source ID').fill('retry_source')
  await page.getByRole('button',{name:'Save source',exact:true}).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('.success-toast')).toHaveCount(0)
  if(failure===401)await page.getByRole('button',{name:'Connect',exact:true}).click()
  await expect(page.getByLabel('Source ID')).toHaveValue('retry_source')
 })
}

test('saved source with failed refresh reports the partial result accurately',async({page})=>{
 let saved=false
 await page.route('**/admin/benchmark/**',async route=>{
  if(route.request().method()==='POST'){saved=true;await route.fulfill({status:201,json:route.request().postDataJSON()});return}
  await route.fulfill(saved?{status:503,json:{detail:'Storage unavailable'}}:{json:{sources:[]}})
 })
 await page.goto('/admin/benchmark')
 await page.getByLabel('Administrator token').fill('x'.repeat(32))
 await page.getByRole('button',{name:'Connect',exact:true}).click()
 await page.getByLabel('Source ID').fill('saved_source')
 await page.getByRole('button',{name:'Save source',exact:true}).click()
 await expect(page.locator('.success-toast')).toContainText('saved successfully')
 await expect(page.getByRole('alert')).toContainText('was saved, but the source list could not be refreshed')
 await expect(page.getByLabel('Source ID')).toHaveValue('')
})
