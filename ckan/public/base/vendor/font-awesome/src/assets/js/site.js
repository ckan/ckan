$(function () {
  $("#newsletter").validate();

  var ads = [
    {
      quote: "<i class='fas fas-perfect fas-2x valign-middle margin-right'></i>Looking for the best icon sets? Check out <strong>Symbolset</strong>, <a href='https://articles.fortawesome.com/fort-awesome-acquires-symbolset-72229dab2c13'>now</a> from the maker of Font Awesome.",
      class: "symbolset",
      url: "https://symbolset.com/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_1_best_icons&utm_campaign=promo_4.6_update",
      btn_text: "Gimme Some!"
    },
    {
      quote: "<i class='fas fas-curate fas-2x valign-middle margin-right'></i>Need a different look for your icons? Check out <strong>Symbolset</strong>, <a href='https://articles.fortawesome.com/fort-awesome-acquires-symbolset-72229dab2c13'>now</a> from the maker of Font Awesome.",
      class: "symbolset",
      url: "https://symbolset.com/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_2_different_look&utm_campaign=promo_4.6_update",
      btn_text: "Gimme Some!"
    },
    // {
    //   quote: "Fort Awesome <a href='#'>acquires</a> Symbolset!",
    //   class: "symbolset",
    //   url: "https://symbolset.com/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_3_acquires&utm_campaign=promo_4.6_update",
    //   btn_text: "Check out Symbolset"
    // },
    // {
    //   quote: "<a href='#' class='no-underline'>Fort Awesome <i class='fa fa-plus fa-lg'></i> Symbolset = <i class='fa fa-heart fa-lg'></i></a>",
    //   class: "symbolset",
    //   url: "https://symbolset.com/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_4_math&utm_campaign=promo_4.6_update",
    //   btn_text: "Check out Symbolset"
    // },


    // {
    //   quote: "Take your icon game to the next level. Check out <strong>Fort Awesome</strong>, from the maker of Font Awesome.",
    //   class: "fort-awesome",
    //   url: "https://fortawesome.com/start?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_1_next_level&utm_campaign=promo_4.6_update",
    //   btn_text: "Gimme Some!"
    // },
    // {
    //   quote: "Make your icons load 10x faster! Check out <strong>Fort Awesome</strong>, from the maker of Font Awesome.",
    //   class: "fort-awesome",
    //   url: "https://fortawesome.com/start?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_3_faster_loading&utm_campaign=promo_4.6_update",
    //   btn_text: "Gimme Some!"
    // },
    // {
    //   quote: "Looking for other great icon sets? Check out <strong>Fort Awesome</strong>, from the maker of Font Awesome.",
    //   class: "fort-awesome",
    //   url: "https://fortawesome.com/start?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_4_more_icons&utm_campaign=promo_4.6_update",
    //   btn_text: "Gimme Some!"
    // },
    // {
    //   quote: "Want to add your own icon? Check out <strong>Fort Awesome</strong>, from the maker of Font Awesome.",
    //   class: "fort-awesome",
    //   url: "https://fortawesome.com/start?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_6_your_own_icon&utm_campaign=promo_4.6_update",
    //   btn_text: "Gimme Some!"
    // },
    //
    //
    // {
    //   quote: "<strong>Black Tie</strong>, from the creator of Font Awesome. On sale at the Kickstarter price for a limited time.",
    //   class: "black-tie",
    //   url: "http://blacktie.io/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_2_kickstarter&utm_campaign=promo_4.6_update",
    //   btn_text: "Check it Out!"
    // },
    // {
    //   quote: "Want clean, minimalist icons? Check out <strong>Black Tie</strong>, the new multi-weight icon font from the maker of Font Awesome.",
    //   class: "black-tie",
    //   url: "http://blacktie.io/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_5_clean_minimalist&utm_campaign=promo_4.6_update",
    //   btn_text: "Check it Out!"
    // },
    // {
    //   quote: "Want a different icon look? Check out <strong>Black Tie</strong>, our new multi-weight icon set.",
    //   class: "black-tie",
    //   url: "http://blacktie.io/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_6_different_look&utm_campaign=promo_4.6_update",
    //   btn_text: "Check it Out!"
    // },
    // {
    //   quote: "Check out <strong>Black Tie</strong>, our new multi-weight icon set!",
    //   class: "black-tie",
    //   url: "http://blacktie.io/?utm_source=font_awesome_homepage&utm_medium=display&utm_content=ad_7_our_new_multi_weight&utm_campaign=promo_4.6_update",
    //   btn_text: "Check it Out!"
    // }
  ];

  selectAd();

  // start the icon carousel
  $('#icon-carousel').carousel({
    interval: 5000
  });

  $('[data-toggle="tooltip"]').tooltip();
  $('[data-toggle="popover"]').popover();

  function selectAd() {
    random_number = Math.floor(Math.random() * ads.length);
    random_ad = ads[random_number];

    $('#banner').addClass(random_ad.class);
    $('#rotating-message').html(random_ad.quote);
    $('#rotating-url').attr("href", random_ad.url);
    $('#rotating-url').html(random_ad.btn_text);
    $('#banner').collapse('show');
  }
});
