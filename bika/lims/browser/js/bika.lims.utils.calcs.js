
/* Please use this command to compile this file into the parent `js` directory:
    coffee --no-header -w -o ../ -c bika.lims.utils.calcs.coffee
 */

(function() {
  window.CalculationUtils = function() {
    var that;
    that = this;
    that.load = function() {
      $(".state-retracted .ajax_calculate").removeClass('ajax_calculate');
      $(".ajax_calculate").live('focus', function() {
        $(this).attr('focus_value', $(this).val());
        $(this).addClass("ajax_calculate_focus");
      });
      $(".ajax_calculate").live('blur', function() {
        if ($(this).attr('focus_value') === $(this).val()) {
          $(this).removeAttr("focus_value");
          $(this).removeClass("ajax_calculate_focus");
        }
      });
      $(".ajax_calculate").live('change', function() {
        var field, form, i, item_data, options, results, uid, value;
        $(this).removeAttr("focus_value");
        $(this).removeClass("ajax_calculate_focus");
        form = $(this).parents("form");
        uid = $(this).attr('uid');
        field = $(this).attr('field');
        value = $(this).attr('value');
        item_data = $(this).parents('table').prev('input[name="item_data"]').val();
        $(".bika-alert").filter("span[uid='" + uid + "']").empty();
        if ($(this).parents('td,div').first().hasClass('interim')) {
          item_data = $.parseJSON(item_data);
          for (i in item_data[uid]) {
            if (item_data[uid][i]['keyword'] === field) {
              item_data[uid][i]['value'] = value;
              item_data = $.toJSON(item_data);
              $(this).parents('table').prev('input[name="item_data"]').val(item_data);
              break;
            }
          }
        }
        results = {};
        $.each($("td:not(.state-retracted) input[field='Result'], td:not(.state-retracted) select[field='Result']"), function(i, e) {
          var andls, defandls, dlop, local_uid, mapping, res, result, tryldl, tryudl;
          local_uid = $(e).attr('uid');
          result = $(e).val().trim();
          defandls = {
            default_ldl: 0,
            default_udl: 100000,
            dlselect_allowed: false,
            manual_allowed: false,
            is_ldl: false,
            is_udl: false,
            below_ldl: false,
            above_udl: false
          };
          andls = $('input[id^="AnalysisDLS."][uid="' + local_uid + '"]');
          andls = andls.length > 0 ? andls.first().val() : null;
          andls = andls !== null ? $.parseJSON(andls) : defandls;
          dlop = $('select[name^="DetectionLimit."][uid="' + local_uid + '"]');
          if (dlop.length > 0) {
            andls.is_ldl = false;
            andls.is_udl = false;
            andls.below_ldl = false;
            andls.above_udl = false;
            tryldl = result.lastIndexOf('<', 0) === 0;
            tryudl = result.lastIndexOf('>', 0) === 0;
            if (tryldl || tryudl) {
              res = result.substring(1);
              if (!isNaN(parseFloat(res))) {
                result = '' + parseFloat(res);
                if (andls.manual_allowed === true) {
                  andls.is_ldl = tryldl;
                  andls.is_udl = tryudl;
                  andls.below_ldl = tryldl;
                  andls.above_udl = tryudl;
                } else {
                  $(e).val(result);
                }
              }
            } else {
              andls.is_ldl = false;
              andls.is_udl = false;
              andls.below_ldl = false;
              andls.above_udl = false;
              if (!isNaN(parseFloat(result))) {
                dlop = dlop.first().val().trim();
                if (dlop === '<' || dlop === '>') {
                  andls.is_ldl = dlop === '<';
                  andls.is_udl = dlop === '>';
                  andls.below_ldl = andls.is_ldl;
                  andls.above_udl = andls.is_udl;
                } else {
                  result = parseFloat(result);
                  andls.below_ldl = result < andls.default_ldl;
                  andls.above_udl = result > andls.default_udl;
                  result = '' + result;
                }
              }
            }
          } else if (!isNaN(parseFloat(result))) {
            result = parseFloat(result);
            andls.is_ldl = false;
            andls.is_udl = false;
            andls.below_ldl = result < andls.default_ldl;
            andls.above_udl = result > andls.default_udl;
            result = '' + result;
          }
          mapping = {
            keyword: $(e).attr('objectid'),
            result: result,
            isldl: andls.is_ldl,
            isudl: andls.is_udl,
            ldl: andls.is_ldl ? result : andls.default_ldl,
            udl: andls.is_udl ? result : andls.default_udl,
            belowldl: andls.below_ldl,
            aboveudl: andls.above_udl
          };
          results[local_uid] = mapping;
        });
        options = {
          type: 'POST',
          url: 'listing_string_entry',
          data: {
            '_authenticator': $('input[name="_authenticator"]').val(),
            'uid': uid,
            'field': field,
            'value': value,
            'results': $.toJSON(results),
            'item_data': item_data,
            'specification': $(".specification").filter(".selected").attr("value")
          },
          dataType: "json",
          success: function(data, textStatus, $XHR) {
            var result, u;
            for (i in $(data['results'])) {
              result = $(data['results'])[i];
              $(".bika-alert").filter("span[uid='" + result.uid + "']").empty();
            }
            $.each(data['alerts'], function(auid, alerts) {
              var lert;
              for (i in alerts) {
                lert = alerts[i];
                $("span[uid='" + auid + "']").filter("span[field='" + lert.field + "']").append("<img src='" + window.portal_url + "/" + lert.icon + "' title='" + lert.msg + "' uid='" + auid + "'/>");
              }
            });
            for (i in $(data['uncertainties'])) {
              u = $(data['uncertainties'])[i];
              $('#' + u.uid + "-uncertainty").val(u.uncertainty);
              $('[uid="' + u.uid + '"][field="Uncertainty"]').val(u.uncertainty);
            }
            for (i in $(data['results'])) {
              result = $(data['results'])[i];
              $("input[uid='" + result.uid + "']").filter("input[field='Result']").val(result.result);
              $('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").val(result.dry_result);
              $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").siblings()[0]).empty().append(result.dry_result);
              if (result.dry_result !== '') {
                $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").siblings().filter(".after")).empty().append("<em class='discreet'>%</em>");
              }
              $("input[uid='" + result.uid + "']").filter("input[field='formatted_result']").val(result.formatted_result);
              $("span[uid='" + result.uid + "']").filter("span[field='formatted_result']").empty().append(result.formatted_result);
              if (result.result !== '' && result.result !== "") {
                if ($("[id*='cb_" + result.uid + "']").prop("checked") === false) {
                  $("[id*='cb_" + result.uid + "']").prop('checked', true);
                }
              }
            }
            if ($('.ajax_calculate_focus').length > 0) {
              if ($(form).attr('submit_after_calculation')) {
                $('#submit_transition').click();
              }
            }
          }
        };
        $.ajax(options);
      });
    };
  };

}).call(this);
