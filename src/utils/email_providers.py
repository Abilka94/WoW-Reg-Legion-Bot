"""
База известных почтовых провайдеров
Сгруппирована по русским и иностранным провайдерам
"""

# Русские почтовые провайдеры
RUSSIAN_PROVIDERS = {
    # Yandex
    'yandex.com',
    'yandex.ru',
    'yandex.by',
    'yandex.kz',
    'yandex.ua',
    'ya.ru',
    
    # Mail.ru
    'mail.ru',
    'inbox.ru',
    'list.ru',
    'bk.ru',
    'e.mail.ru',
    'internet.ru',
    
    # Rambler
    'rambler.ru',
    'rambler.ua',
    
    # Другие русские провайдеры
    'pochta.ru',
    'sibmail.com',
    'narod.ru',
    
    # Украинские провайдеры
    'ukr.net',
    'i.ua',
    'meta.ua',
    'bigmir.net',
    'online.ua',
    'ex.ua',
    'ukrpost.ua',
    'mail.ua',
    'email.ua',
    
    # Белорусские провайдеры
    'mail.by',
    'tut.by',
    
    # Казахстанские провайдеры
    'mail.kz',
    
    # Другие страны СНГ
    'mail.kg',
    'mail.uz',
    'mail.tj',
    'mail.am',
    'mail.az',
    'mail.ge',
    'mail.md',
}

# Иностранные почтовые провайдеры
FOREIGN_PROVIDERS = {
    # Популярные международные
    'gmail.com',
    'googlemail.com',
    
    # Yahoo
    'yahoo.com',
    'yahoo.co.uk',
    'yahoo.fr',
    'yahoo.de',
    'yahoo.it',
    'yahoo.es',
    'yahoo.ro',
    
    # Microsoft (Outlook/Hotmail)
    'outlook.com',
    'hotmail.com',
    'hotmail.co.uk',
    'hotmail.fr',
    'hotmail.de',
    'live.com',
    'msn.com',
    
    # Другие популярные
    'mail.com',
    'email.com',
    'inbox.com',
    'zoho.com',
    'protonmail.com',
    'proton.me',
    'icloud.com',
    'me.com',
    'mac.com',
    'aol.com',
    'aol.co.uk',
    'aol.fr',
    'aol.de',
    
    # Немецкие провайдеры
    'gmx.com',
    'gmx.de',
    'gmx.fr',
    'gmx.net',
    'web.de',
    't-online.de',
    'freenet.de',
    'arcor.de',
    '1und1.de',
    
    # Итальянские провайдеры
    'tiscali.it',
    'libero.it',
    'alice.it',
    'virgilio.it',
    
    # Испанские провайдеры
    'tiscali.es',
    'terra.es',
    'telefonica.net',
    
    # Французские провайдеры
    'orange.fr',
    'wanadoo.fr',
    'laposte.net',
    'sfr.fr',
    'free.fr',
    
    # Британские провайдеры
    'mail.co.uk',
    'btinternet.com',
    'virgin.net',
    'talk21.com',
    'tiscali.co.uk',
    
    # Польские провайдеры
    'mail.pl',
    'wp.pl',
    'o2.pl',
    'interia.pl',
    'gazeta.pl',
    'onet.pl',
    'poczta.onet.pl',
    'tlen.pl',
    
    # Чешские провайдеры
    'mail.cz',
    'seznam.cz',
    'centrum.cz',
    'email.cz',
    'post.cz',
    
    # Словацкие провайдеры
    'mail.sk',
    'azet.sk',
    'centrum.sk',
    'post.sk',
    
    # Венгерские провайдеры
    'mail.hu',
    'freemail.hu',
    'citromail.hu',
    'vipmail.hu',
    
    # Румынские провайдеры
    'mail.ro',
    'gmail.ro',
    'zappmobile.ro',
    
    # Болгарские провайдеры
    'mail.bg',
    'abv.bg',
    'dir.bg',
    
    # Сербские провайдеры
    'mail.rs',
    'eunet.rs',
    
    # Хорватские провайдеры
    'mail.hr',
    't-com.hr',
    
    # Словенские провайдеры
    'mail.si',
    'siol.net',
    
    # Финские провайдеры
    'mail.fi',
    'luukku.com',
    
    # Норвежские провайдеры
    'mail.no',
    'online.no',
    
    # Датские провайдеры
    'mail.dk',
    
    # Шведские провайдеры
    'mail.se',
    
    # Исландские провайдеры
    'mail.is',
    
    # Португальские провайдеры
    'mail.pt',
    'sapo.pt',
    'clix.pt',
    
    # Греческие провайдеры
    'mail.gr',
    'otenet.gr',
    
    # Израильские провайдеры
    'mail.co.il',
    'walla.co.il',
    
    # Азиатские провайдеры
    'qq.com',
    '163.com',
    '126.com',
    'sina.com',
    'naver.com',
    'daum.net',
    'mail.co.jp',
    'mail.co.kr',
    'mail.co.in',
    'mail.co.id',
    'mail.co.th',
    'mail.co.vn',
    'mail.co.ph',
    'mail.com.sg',
    'mail.com.my',
    'mail.com.tw',
    'mail.com.hk',
    
    # Африканские провайдеры
    'mail.co.za',
    
    # Австралийские и новозеландские провайдеры
    'mail.com.au',
    'mail.co.nz',
    
    # Латиноамериканские провайдеры
    'mail.com.mx',
    'mail.com.ar',
    'mail.com.br',
    'mail.com.co',
    'mail.com.ve',
    'mail.com.pe',
    'mail.com.cl',
    'mail.com.ec',
    'mail.com.uy',
    'mail.com.py',
    'mail.com.bo',
    'mail.com.cr',
    'mail.com.gt',
    'mail.com.hn',
    'mail.com.ni',
    'mail.com.pa',
    'mail.com.do',
    'mail.com.sv',
    'mail.com.pr',
    'mail.com.cu',
    'mail.com.jm',
    'mail.com.tt',
    'mail.com.bb',
    'mail.com.bz',
    'mail.com.gy',
    'mail.com.sr',
    
    # Другие популярные сервисы
    'rediffmail.com',
    'tutanota.com',
    'fastmail.com',
    'hushmail.com',
    'mailfence.com',
    'runbox.com',
    
    # Прибалтийские провайдеры
    'inbox.lv',
    'apollo.lv',
    'inbox.lt',
    'takas.lt',
    'mail.ee',
    'zone.ee',
}

# Объединенный список всех известных провайдеров
KNOWN_EMAIL_PROVIDERS = RUSSIAN_PROVIDERS | FOREIGN_PROVIDERS
