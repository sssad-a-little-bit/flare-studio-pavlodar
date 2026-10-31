import { localUrl } from './paths';
import type { InquiryConfig } from './types';

const form: InquiryConfig = {
  id: 'picasso-inquiry',
  eyebrow: 'Давайте знакомиться',
  title: 'С чего начнётся\nваша история?',
  description: 'Расскажите немного об интересах ребёнка. Соберём вопросы в одно обращение — его можно будет отредактировать и скопировать.',
  fields: [
    { name: 'age', label: 'Примерный возраст ребёнка', placeholder: 'Например, около 7 лет', required: true, type: 'text', maxLength: 80 },
    { name: 'interests', label: 'Что ему интересно?', placeholder: 'Цвет, рисунки, придумывать что-то своё…', required: true, type: 'text', maxLength: 240 },
    { name: 'wishes', label: 'Ваши вопросы и пожелания', placeholder: 'Что вы хотели бы узнать о занятиях?', required: true, type: 'textarea', maxLength: 1500 },
    { name: 'time', label: 'Удобное время для связи', placeholder: 'Например, в будни после 17:00', type: 'text', maxLength: 120 },
  ],
  submitLabel: 'Составить обращение',
  greeting: 'Здравствуйте! Хочу узнать о занятиях Picasso.',
  lines: [
    { field: 'age', prefix: 'Примерный возраст ребёнка' },
    { field: 'interests', prefix: 'Ему интересно' },
    { field: 'wishes', prefix: 'Вопросы и пожелания' },
    { field: 'time', prefix: 'Удобное время для связи' },
  ],
  closing: 'Подскажите, пожалуйста, какие занятия могут подойти и на каких условиях они проходят.',
};

export const picasso = {
  name: 'Picasso',
  title: 'Picasso — творческая студия в Павлодаре',
  descriptor: 'детская творческая студия',
  city: 'Павлодар',
  phone: '+7 701 751 70 52',
  phoneHref: '+77017517052',
  address: 'ул. Лермонтова, 99',
  instagram: 'https://www.instagram.com/picasso_art_pavlodar/',
  instagramLabel: '@picasso_art_pavlodar',
  map: 'https://yandex.kz/maps/?text=Павлодар%20Лермонтова%2099',
  navLabel: 'Навигация по студии Picasso',
  nav: [
    { href: '#atmosphere', label: 'Настроение' },
    { href: '#how-to-choose', label: 'С чего начать' },
    { href: '#contacts', label: 'Контакты' },
  ],
  switchLabel: 'Концепт Batyr Studio',
  switchHref: localUrl('batyr/'),
  hero: {
    eyebrow: 'Творческая студия в Павлодаре',
    title: ['Место для', 'первых', 'творческих', 'открытий'],
    text: 'Большое воображение начинается с маленького «а что, если?».',
    primary: 'Узнать о занятиях',
    secondary: 'Посмотреть работы',
    externalNote: 'В Instagram ↗',
    aside: 'У каждого открытия\nсвой цвет.',
    image: localUrl('art/picasso-paper.svg'),
    imageAlt: 'Нейтральная художественная композиция: ультрамариновый мазок, терракотовая линия и охристый круг на бумаге',
    caption: 'Иллюстрация',
    captionDetail: 'Цвет, линия и немного воображения',
    scroll: 'Листайте, здесь есть место для идей',
  },
  atmosphere: {
    eyebrow: 'Настроение мастерской',
    title: 'А если солнце\nбудет синим?',
    text: 'Чистый лист — это приглашение придумать своё. Попробовать другой цвет. Увидеть что-то необычное в самом обычном.',
    note: 'Немного любопытства.\nМного возможностей.',
    image: localUrl('art/picasso-study.svg'),
    imageAlt: 'Иллюстрация бумажного натюрморта: синий сосуд, терракотовый круг и охристые линии',
    caption: 'Иллюстрация',
    workText: 'Настоящие работы расскажут больше любых слов. Познакомиться со студией можно в её Instagram.',
    workLink: 'Заглянуть в Instagram',
  },
  steps: {
    eyebrow: 'С чего начать',
    title: 'Найдём первую\nточку на листе.',
    intro: 'Чтобы узнать о подходящем занятии, начните с небольшого разговора.',
    items: [
      { number: '01', title: 'Расскажите о ребёнке', text: 'Примерный возраст, любимые занятия и то, что вызывает любопытство.' },
      { number: '02', title: 'Задайте свои вопросы', text: 'О формате, программах, расписании и стоимости — обо всём, что важно для вас.' },
      { number: '03', title: 'Уточните условия', text: 'Обсудите со студией подходящий вариант и договоритесь о следующем шаге.' },
    ],
  },
  form,
  contacts: {
    eyebrow: 'На связи',
    title: 'Приходите\nс любопытством.',
    locationLabel: 'Где искать',
    phoneLabel: 'Обсудить занятия',
    mapLabel: 'Открыть на карте',
    instagramLabel: 'Заглянуть в студию',
    note: 'Адрес и телефон взяты из публичного каталога и требуют подтверждения владельцем. Перед визитом уточните адрес и время работы.',
  },
  footer: {
    concept: 'Демонстрационный концепт Flare Studio',
    contact: '@cvc_io',
    date: 'Проверка источников: 31.10.2026',
  },
  mobileAction: 'Узнать о занятиях',
  arrowLabel: 'Перейти к форме обращения',
};



