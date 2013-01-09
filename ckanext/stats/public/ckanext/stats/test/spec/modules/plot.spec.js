/*globals describe before beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.PlotModule()', function () {
  var PlotModule = ckan.module.registry['plot'];

  before(function (done) {
    var _this = this;

    jQuery.get('./fixtures/table.html', function (html) {
      _this.template = html;
      done();
    });
  });

  beforeEach(function () {
    this.el = jQuery(this.template).appendTo(this.fixture);
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new PlotModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should setup the canvas element', function () {
      var target = sinon.stub(this.module, 'setupCanvas', this.module.setupCanvas);

      this.module.initialize();
      assert.called(target);
    });

    it('should draw the graph', function () {
      var target = sinon.stub(this.module, 'draw');

      this.module.initialize();
      assert.called(target);
    });

    it('should listen for "shown" events on the body', function () {
      var target = sinon.stub(this.sandbox.body, 'on');

      this.module.initialize();
      assert.called(target);
      assert.calledWith(target, "shown", this.module._onShown);
    });
  });

  describe('.teardown()', function () {
    it('should remove "shown" listeners from the body', function () {
      var target = sinon.stub(this.sandbox.body, 'off');

      this.module.teardown();
      assert.called(target);
      assert.calledWith(target, "shown", this.module._onShown);
    });
  });

  describe('.setupCanvas()', function () {
    it('should create the .canvas element', function () {
      this.module.setupCanvas();

      assert.isDefined(this.module.canvas);
      assert.isDefined(this.module.canvas.is('div'));
    });

    it('should replace the .el with the .canvas', function () {
      this.module.setupCanvas();
      assert.ok(jQuery.contains(this.sandbox.body[0], this.module.canvas[0]));
    });
  });

  describe('.draw()', function () {
    beforeEach(function () {
      this.plot = {};
      this.module.canvas = jQuery('<div />').appendTo(this.fixture);
      jQuery.plot = sinon.stub().returns(this.plot);
    });

    it('should call jQuery.plot() if the canvas is visible', function () {
      this.module.draw();

      assert.called(jQuery.plot);
      assert.calledWith(jQuery.plot, this.module.canvas, this.module.data, this.module.options);
    });

    it('should assign the .graph property', function () {
      this.module.draw();
      assert.strictEqual(this.module.graph, this.plot);
    });

    it('should not call jQuery.plot() if the canvas is not visible', function () {
      this.module.canvas.hide();
      this.module.draw();

      assert.notCalled(jQuery.plot);
    });
  });

  describe('.parseTable(table)', function () {
    it('should parse the contents of the provided table', function () {
      var target = this.module.parseTable(this.module.el);

      assert.deepEqual(target, [{
        label: 'Series A Legend',
        data: [
          [new Date(1176073200000), "20"],
          [new Date(1176678000000), "12"],
          [new Date(1177282800000), "27"]
        ]
      }, {
        label: 'Series B Legend',
        data: [
          [new Date(1176073200000), "7"],
          [new Date(1176678000000), "6"],
          [new Date(1177282800000), "12"]
        ]
      }]);
    });
  });

  describe('.getValue(cell)', function () {
    it('should extract the value from a table cell');
    it('should use the data-value attribute if present');
    it('should parse the value using the data-type');
  });

  describe('.parseValue(value, type)', function () {
    it('should create a date object if type == "date"');
    it('should return the value if the type is not recognised');
  });

  describe('._onShown(event)', function () {
    it('should call .draw() if the event.target contains the canvas');
  });
});
