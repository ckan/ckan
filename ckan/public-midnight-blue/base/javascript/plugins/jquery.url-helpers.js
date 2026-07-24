/* .slugify() based on jQuery Slugify a string! by Pablo Bandin
 *
 * See: http://tracehello.wordpress.com/2011/06/15/jquery-real-slugify-plugin/
 *
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 */
(function ($, window) {
  $.url = {
    /* Escapes a string for use in a url component. All special characters
     * are url encoded and spaces are replaced by a plus rather than a %20.
     *
     * string - A string to convert.
     *
     * Examples
     *
     *   jQuery.url.escape('apples & pears'); //=> "apples+%26+pears"
     *
     * Returns the escaped string.
     */
    escape: function (string) {
      return window.encodeURIComponent(string || '').replace(/%20/g, '+');
    },

    /* Converts a string into a url compatible slug. Characters that cannot
     * be converted will be replaced by hyphens.
     *
     * string - The string to convert.
     * trim   - Remove starting, trailing and duplicate hyphens (default: true)
     *
     * Examples
     *
     *   jQuery.url.slugify('apples & pears'); //=> 'apples-pears'
     *
     * Returns the new slug.
     */
    slugify: function (string, trim) {
      var str = '';
      var index = 0;
      var length = string.length;
      var map = this.map;

      for (;index < length; index += 1) {
        str += map[string.charCodeAt(index).toString(16)] || '-';
      }

      str = str.toLowerCase();

      return trim === false ? str : str.replace(/\-+/g, '-').replace(/^-|-$/g, '');
    }
  };

  // The following takes two sets of characters, the first a set of hexadecimal
  // Unicode character points, the second their visually similar counterparts.
  // I'm not 100% sure this is the best way to handle such characters but
  // it seems to be a common practice.
  var unicode = ('20 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 ' +
      '47 48 49 50 51 52 53 54 55 56 57 58 59 61 62 63 64 65 66 67 68 69 70 ' +
      '71 72 73 74 75 76 77 78 79 100 101 102 103 104 105 106 107 108 109 ' +
      '110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 ' +
      '126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 ' +
      '142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 ' +
      '158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 ' +
      '174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 ' +
      '190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 ' +
      '206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 ' +
      '222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 ' +
      '238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 ' +
      '254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 ' +
      '270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 ' +
      '286 287 288 289 290 291 292 293 294 295 296 297 298 299 363 364 ' +
      '365 366 367 368 369 386 388 389 390 391 392 393 394 395 396 397 ' +
      '398 399 400 401 402 403 404 405 406 407 408 409 410 411 412 413 ' +
      '414 415 416 417 418 419 420 421 422 423 424 425 426 427 428 429 ' +
      '430 431 432 433 434 435 436 437 438 439 440 441 442 443 444 445 ' +
      '446 447 448 449 450 451 452 453 454 455 456 457 458 459 460 461 ' +
      '462 463 464 465 466 467 468 469 470 471 472 473 474 475 476 477 ' +
      '478 479 480 481 490 491 492 493 494 495 496 497 498 499 500 501 ' +
      '502 503 504 505 506 507 508 509 510 511 512 513 514 515 531 532 ' +
      '533 534 535 536 537 538 539 540 541 542 543 544 545 546 547 548 ' +
      '549 550 551 552 553 554 555 556 561 562 563 564 565 566 567 568 ' +
      '569 570 571 572 573 574 575 576 577 578 579 580 581 582 583 584 ' +
      '585 586 587 4a 4b 4c 4d 4e 4f 5a 6a 6b 6c 6d 6e 6f 7a a2 a3 a5 a7 ' +
      'a9 aa ae b2 b3 b5 b6 b9 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 ca cb cc cd ' +
      'ce cf d0 d1 d2 d3 d4 d5 d6 d7 d8 d9 da db dc dd de df e0 e1 e2 e3 ' +
      'e4 e5 e6 e7 e8 e9 ea eb ec ed ee ef f0 f1 f2 f3 f4 f5 f6 f8 f9 fa ' +
      'fb fc fd ff 10a 10b 10c 10d 10e 10f 11a 11b 11c 11d 11e 11f 12a ' +
      '12b 12c 12d 12e 12f 13a 13b 13c 13d 13e 13f 14a 14b 14c 14d 14e ' +
      '14f 15a 15b 15c 15d 15e 15f 16a 16b 16c 16d 16e 16f 17a 17b 17c ' +
      '17d 17e 17f 18a 18b 18c 18d 18e 18f 19a 19b 19c 19d 19e 19f 1a0 ' +
      '1a1 1a2 1a3 1a4 1a5 1a6 1a7 1a8 1a9 1aa 1ab 1ac 1ad 1ae 1af 1b0 ' +
      '1b1 1b2 1b3 1b4 1b5 1b6 1b7 1b8 1b9 1ba 1bb 1bc 1bd 1be 1bf 1c4 ' +
      '1c5 1c6 1c7 1c8 1c9 1ca 1cb 1cc 1cd 1ce 1cf 1d0 1d1 1d2 1d3 1d4 ' +
      '1d5 1d6 1d7 1d8 1d9 1da 1db 1dc 1dd 1de 1df 1e0 1e1 1e2 1e3 1e4 ' +
      '1e5 1e6 1e7 1e8 1e9 1ea 1eb 1ec 1ed 1ee 1ef 1f0 1f1 1f2 1f3 1f4 ' +
      '1f5 1f6 1f7 1f8 1f9 1fa 1fb 1fc 1fd 1fe 1ff 20a 20b 20c 20d 20e ' +
      '20f 21a 21b 21c 21d 21e 21f 22a 22b 22c 22d 22e 22f 23a 23b 23c ' +
      '23d 23e 23f 24a 24b 24c 24d 24e 24f 25a 25b 25c 25d 25e 25f 26a ' +
      '26b 26c 26d 26e 26f 27a 27b 27c 27d 27e 27f 28a 28b 28c 28d 28e ' +
      '28f 29a 29b 29c 29d 29e 29f 2a0 2a1 2a2 2a3 2a4 2a5 2a6 2a7 2a8 ' +
      '2a9 2aa 2ab 2ac 2ae 2af 2b0 2b1 2b2 2b3 2b4 2b5 2b6 2b7 2b8 2df ' +
      '2e0 2e1 2e2 2e3 2e4 36a 36b 36c 36d 36e 36f 37b 37c 37d 38a 38c ' +
      '38e 38f 39a 39b 39c 39d 39e 39f 3a0 3a1 3a3 3a4 3a5 3a6 3a7 3a8 ' +
      '3a9 3aa 3ab 3ac 3ad 3ae 3af 3b0 3b1 3b2 3b3 3b4 3b5 3b6 3b7 3b8 ' +
      '3b9 3ba 3bb 3bc 3bd 3be 3bf 3c0 3c1 3c2 3c3 3c4 3c5 3c6 3c7 3c8 ' +
      '3c9 3ca 3cb 3cc 3cd 3ce 3d0 3d1 3d2 3d3 3d4 3d5 3d6 3d7 3d8 3d9 ' +
      '3da 3db 3dc 3dd 3de 3df 3e2 3e3 3e4 3e5 3e6 3e7 3e8 3e9 3ea 3eb ' +
      '3ec 3ed 3ee 3ef 3f0 3f1 3f2 3f3 3f4 3f5 3f6 3f7 3f8 3f9 3fa 3fb ' +
      '3fc 3fd 3fe 3ff 40a 40b 40c 40d 40e 40f 41a 41b 41c 41d 41e 41f ' +
      '42a 42b 42c 42d 42e 42f 43a 43b 43c 43d 43e 43f 44a 44b 44c 44d ' +
      '44e 44f 45a 45b 45c 45d 45e 45f 46a 46b 46c 46d 46e 46f 47a 47b ' +
      '47c 47d 47e 47f 48a 48b 48c 48d 48e 48f 49a 49b 49c 49d 49e 49f ' +
      '4a0 4a1 4a2 4a3 4a4 4a5 4a6 4a7 4a8 4a9 4aa 4ab 4ac 4ad 4ae 4af ' +
      '4b0 4b1 4b2 4b3 4b4 4b5 4b6 4b7 4b8 4b9 4ba 4bb 4bc 4bd 4be 4bf ' +
      '4c0 4c1 4c2 4c3 4c4 4c5 4c6 4c7 4c8 4c9 4ca 4cb 4cc 4cd 4ce 4cf ' +
      '4d0 4d1 4d2 4d3 4d4 4d5 4d6 4d7 4d8 4d9 4da 4db 4dc 4dd 4de 4df ' +
      '4e0 4e1 4e2 4e3 4e4 4e5 4e6 4e7 4e8 4e9 4ea 4eb 4ec 4ed 4ee 4ef ' +
      '4f0 4f1 4f2 4f3 4f4 4f5 4f6 4f7 4f8 4f9 4fa 4fb 4fc 4fd 4fe 4ff ' +
      '50a 50b 50c 50d 50e 50f 51a 51b 51c 51d 53a 53b 53c 53d 53e 53f ' +
      '54a 54b 54c 54d 54e 54f 56a 56b 56c 56d 56e 56f 57a 57b 57c 57d ' +
      '57e 57f 5f').split(' ');

  var replacement = ('- 0 1 2 3 4 5 6 7 8 9 A B C D E F G H I P Q R S T ' +
      'U V W X Y a b c d e f g h i p q r s t u v w x y A a A a A a C c C c ' +
      'D d E e E e E e E e G g G g H h H h I i I i IJ ij J j K k k L l L l ' +
      'N n N n N n n O o OE oe R r R r R r S s T t T t T t U u U u U u W w ' +
      'Y y Y Z b B b b b b C C c D E F f G Y h i I K k A a A a E e E e I i ' +
      'R r R r U u U u S s n d 8 8 Z z A a E e O o Y y l n t j db qp < ? ? ' +
      'B U A E e J j a a a b c e d d e e g g g Y x u h h i i w m n n N o oe ' +
      'm o r R R S f f f f t t u Z Z 3 3 ? ? 5 C O B a e i o u c d A ' +
      'E H i A B r A E Z H O I E E T r E S I I J jb A B B r D E X 3 N N P ' +
      'C T y O X U h W W a 6 B r d e x 3 N N P C T Y qp x U h W W e e h r ' +
      'e s i i j jb W w Tb tb IC ic A a IA ia Y y O o V v V v Oy oy C c R ' +
      'r F f H h X x 3 3 d d d d R R R R JT JT E e JT jt JX JX U D Q N T ' +
      '2 F r p z 2 n x U B j t n C R 8 R O P O S w f q n t q t n p h a n ' +
      'a u j u 2 n 2 n g l uh p o S u J K L M N O Z j k l m n o z c f Y s ' +
      'c a r 2 3 u p 1 A A A A A A AE C E E E E I I I I D N O O O O O X O ' +
      'U U U U Y p b a a a a a a ae c e e e e i i i i o n o o o o o o u u ' +
      'u u y y C c C c D d E e G g G g I i I i I i l L l L l L n n O o O ' +
      'o S s S s S s U u U u U u z Z z Z z f D d d q E e l h w N n O O o ' +
      'P P P p R S s E l t T t T U u U U Y y Z z 3 3 3 3 2 5 5 5 p DZ Dz ' +
      'dz Lj Lj lj NJ Nj nj A a I i O o U u U u U u U u U u e A a A a AE ' +
      'ae G g G g K k Q q Q q 3 3 J dz dZ DZ g G h p N n A a AE ae O o I ' +
      'i O o O o T t 3 3 H h O o O o O o A C c L T s Q q R r Y y e 3 3 3 ' +
      '3 j i I I I h w R r R R r r u v A M Y Y B G H j K L q ? c dz d3 dz ' +
      'ts tf tc fn ls lz ww u u h h j r r r R W Y x Y 1 s x c h m r t v x ' +
      'c c c I O Y O K A M N E O TT P E T Y O X Y O I Y a e n i v a b y d ' +
      'e c n 0 1 k j u v c o tt p s o t u q X Y w i u o u w b e Y Y Y O w ' +
      'x Q q C c F f N N W w q q h e S s X x 6 6 t t x e c j O E E p p C ' +
      'M M p C C C Hb Th K N Y U K jI M H O TT b bI b E IO R K JI M H O N ' +
      'b bI b e io r Hb h k n y u mY my Im Im 3 3 O o W w W W H H B b P p ' +
      'K k K k K k K k H h H h Ih ih O o C c T t Y y Y y X x TI ti H h H ' +
      'h H h E e E e I X x K k jt jt H h H h H h M m l A a A a AE ae E e ' +
      'e e E e X X 3 3 3 3 N n N n O o O o O o E e Y y Y y Y y H h R r bI ' +
      'bi F f X x X x H h G g T t Q q W w d r L Iu O y m o N U Y S d h l ' +
      'lu d y w 2 n u y un _').split(' ');

  // Map the Unicode characters to their counterparts in an object.
  var map = {};
  for (var index = 0, length = unicode.length; index < length; index += 1) {
    map[unicode[index]] = replacement[index];
  }

  $.url.map = map;

})(this.jQuery, this);
