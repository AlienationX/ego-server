-- SQLite
select * from wallpaper_classify;

-- 增加 bing必应每日壁纸 分类
delete from wallpaper_classify where id = 30;
insert into wallpaper_classify (id, name, sort, picurl, `select`, enable, created_at, updated_at) values
(30, 'bing必应每日壁纸', 30, 'https', True, True, datetime('now'), datetime('now'));

-- 增加 宝可梦 多个分类
delete from wallpaper_classify where id >= 60;
insert into wallpaper_classify (id, name, sort, picurl, `select`, enable, created_at, updated_at) values
(60, '睡觉sleep', 60, 'https', True, True, datetime('now'), datetime('now')),
(61, '官方壁纸', 61, 'https', True, True, datetime('now'), datetime('now'));
