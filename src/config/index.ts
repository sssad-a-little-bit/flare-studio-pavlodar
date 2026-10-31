import { localUrl } from './paths';
import type { GalleryItem, InquiryConfig } from './types';

export const common = {
  skip: 'Перейти к содержимому',
  demo: 'Демонстрационный концепт Flare Studio',
  flareContact: '@cvc_io',
  otherConcept: 'Другой концепт',
  optional: 'необязательно',
  required: 'Обязательное поле',
  selectDirection: 'Выберите направление',
  emptyError: 'Пожалуйста, заполните это поле.',
  yearError: 'Укажите год от 1900 до 2027 или оставьте поле пустым.',
  summaryTitle: 'Ваше обращение',
  summaryHelp: 'Текст можно отредактировать и скопировать. Затем свяжитесь со студией удобным способом.',
  summaryLabel: 'Редактируемый текст обращения',
  copy: 'Скопировать текст',
  copied: 'Текст скопирован.',
  copyFailed: 'Не удалось скопировать автоматически. Выделите текст и скопируйте его вручную.',
  emptySummary: 'Добавьте текст обращения перед копированием.',
  call: 'Позвонить',
  localOnly: 'Форма ничего не отправляет. Данные остаются на этой странице и исчезнут после её закрытия.',
  regenerate: 'Обновить текст из формы',
  galleryClose: 'Закрыть фотографию',
  galleryLabel: 'Просмотр работы',
};

export const batyr = {
  name: 'Batyr Studio',
  title: 'Batyr Studio — автомобильные плёнки и детейлинг в Павлодаре',
  city: 'Павлодар',
  phone: '+7 771 155 66 66',
  phoneHref: '+77711556666',
  address: 'ул. Кабдеша Нуркина, 57/3',
  instagram: 'https://www.instagram.com/batyr_studio/',
  instagramLabel: '@batyr_studio',
  mapUrl: 'https://yandex.kz/maps/org/batyr_studio/105006396658/',
  nav: [{ label: 'Направления', href: '#directions' }, { label: 'Работы', href: '#works' }, { label: 'Контакты', href: '#contacts' }],
  hero: {
    eyebrow: 'Автомобильные плёнки и детейлинг',
    first: 'Внимание',
    second: 'к каждой',
    accent: 'детали',
    last: 'вашего автомобиля',
    description: 'Внешний вид начинается с деталей. Обсудим, что нужно вашему автомобилю.',
    primary: 'Обсудить задачу',
    secondary: 'Посмотреть работы',
    location: 'Павлодар, Казахстан',
    image: localUrl('art/batyr-body.svg'),
    imageAlt: 'Нейтральная иллюстрация серебристого автомобиля, вид спереди и сбоку',
    imageCaption: 'Иллюстрация',
    imageNote: 'Форма. Свет. Поверхность.',
    bottom: 'Точный подход к внешнему виду',
  },
  directions: {
    eyebrow: 'Направления работы',
    title: 'Поверхность меняет впечатление.',
    note: 'В открытых справочниках упоминаются следующие направления. Возможность выполнения конкретной задачи уточните у студии.',
    items: [
      { title: 'Тонирование', description: 'Обсудите желаемый результат и подходящий вариант для вашего автомобиля.', tag: 'Стекло' },
      { title: 'Защитные плёнки', description: 'Уточните доступные решения, материалы и зоны нанесения.', tag: 'Кузов' },
      { title: 'Автомобильная оптика', description: 'Опишите задачу по оптике — детали и условия нужно согласовать со студией.', tag: 'Свет' },
    ],
    cta: 'Уточнить стоимость',
  },
  works: {
    eyebrow: 'Взгляд на детали',
    title: 'Работу лучше увидеть.',
    description: 'Загляните в Instagram студии, чтобы посмотреть опубликованные материалы и обсудить похожую задачу.',
    cta: 'Работы в Instagram',
    note: 'Фотографии для этого концепта ещё не согласованы. Иллюстрации показывают только визуальную идею сайта.',
    caption: 'Иллюстрация · защитная плёнка на капоте',
    image: localUrl('art/batyr-film.svg'),
    imageAlt: 'Нейтральная иллюстрация нанесения прозрачной защитной плёнки на автомобильный капот с кобальтовым ракелем',
    gallery: [] as GalleryItem[],
  },
  steps: {
    eyebrow: 'От идеи к обсуждению',
    title: 'Начнём с вашего автомобиля.',
    items: [
      { title: 'Опишите автомобиль', text: 'Марка, модель и, если знаете, год выпуска.' },
      { title: 'Расскажите о пожеланиях', text: 'Что хочется изменить и какой результат вам близок.' },
      { title: 'Согласуйте условия', text: 'Уточните со студией возможность работ, стоимость и время.' },
    ],
  },
  form: {
    id: 'batyr-inquiry',
    eyebrow: 'Ваша задача',
    title: 'Начать с разговора.',
    description: 'Пара деталей об автомобиле — и текст обращения готов.',
    fields: [
      { name: 'car', label: 'Марка и модель', placeholder: 'Например, Toyota Camry', required: true, maxLength: 100 },
      { name: 'year', label: 'Год выпуска', placeholder: 'Например, 2020', type: 'year', maxLength: 4 },
      { name: 'direction', label: 'Интересующее направление', type: 'select', required: true, options: ['Тонирование', 'Защитные плёнки', 'Автомобильная оптика', 'Нужна консультация'] },
      { name: 'comment', label: 'Комментарий', placeholder: 'Что хотите обсудить?', type: 'textarea', maxLength: 1500 },
    ],
    submitLabel: 'Подготовить обращение',
    greeting: 'Здравствуйте! Хочу обсудить задачу с Batyr Studio.',
    lines: [{ field: 'car', prefix: 'Автомобиль' }, { field: 'year', prefix: 'Год выпуска' }, { field: 'direction', prefix: 'Интересует' }, { field: 'comment', prefix: 'Пожелания' }],
    closing: 'Подскажите, пожалуйста, возможные варианты и стоимость.',
  } satisfies InquiryConfig,
  contacts: {
    eyebrow: 'Контакты и маршрут',
    title: 'Встретимся в Павлодаре.',
    addressLabel: 'Предварительный адрес',
    phoneLabel: 'Телефон для связи',
    route: 'Построить маршрут',
    note: 'Адрес и телефон из открытых источников. Перед визитом уточните их и время работы у студии.',
    checkDate: 'Данные проверены: 31 октября 2026',
    mapLabel: 'Открыть карточку Batyr Studio в Яндекс Картах',
  },
};

export { picasso } from './picasso';






