# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# Copyright (c) 2018 Reishin <hapy.lestat@gmail.com>


class BaseView(object):
  """
   BaseConfigView is a basic class, which providing Object to Dict, Dict to Object conversion with
   basic fields validation.

   Should be subclassed for proper usage. For example we have such dictionary:

   my_dict = {
     name: "Amy",
     age: 18
   }

   and we want to convert this to the object with populated object fields by key:value pairs from dict.
   For that we need to declare object view and describe there expected fields:

   class PersonView(BaseConfigView):
     name = None
     age = None

    Instead of None, we can assign another values, they would be used as default if  data dict will not contain
     such fields.  Now it's time for conversion:

    PERSON = PersonView(serialized_obj=my_dict)



    As second way to initialize view, view fields could be directly passed as constructor arguments:

    PERSON = PersonView(name=


  """

  def __init__(self, serialized_obj=None, ignore_non_existing=False, **kwargs):
    """
    :type tree dict
    :type ignore_non_existing bool
    """
    if len(kwargs) > 0:
      self.deserialize(kwargs, ignore_non_existing=ignore_non_existing)

    if serialized_obj:
      self.deserialize(serialized_obj, ignore_non_existing=ignore_non_existing)

  @classmethod
  def _isclass(cls, obj, clazz=object):
    try:
      return issubclass(obj, clazz)
    except TypeError:
      return False

  @classmethod
  def deserialize_dict(cls, obj=None, ignore_non_existing=False):
    """
    :type obj dict|None
    :type ignore_non_existing bool
    :rtype cls
    """
    return cls().deserialize(obj, ignore_non_existing)

  def deserialize(self, obj=None, ignore_non_existing=False):
    """
    :type obj dict|None
    :type ignore_non_existing bool
    """
    if not isinstance(obj, dict):
      if ignore_non_existing:
        return

      raise TypeError("Wrong data '{}' passed for '{}' deserialization".format(obj, self.__class__.__name__))

    if obj.__class__ is self.__class__:
      return obj

    definitions = {k: v for k, v in self.__class__.__dict__.items() if k[:1] != "_"}
    def_property_keys = set(definitions.keys())
    property_keys = set(obj.keys())

    existing_keys = def_property_keys & property_keys
    non_defined_keys = property_keys - def_property_keys
    non_existing_keys = def_property_keys - property_keys

    if not ignore_non_existing and non_defined_keys:
      raise TypeError(self.__class__.__name__ + " doesn't contain properties: {}".format(", ".join(non_defined_keys)))

    for k in existing_keys:
      v = obj[k]
      attr_type = definitions[k]

      try:
        if isinstance(attr_type, list) and self._isclass(attr_type[0], BaseView):
          obj_list = [attr_type[0](serialized_obj=v_item) for v_item in v] if isinstance(v, list) else [attr_type[0](serialized_obj=v)]
          self.__setattr__(k, obj_list)
        elif self._isclass(attr_type, BaseView):
          self.__setattr__(k, attr_type(v))
        else:
          self.__setattr__(k, v)
      except IndexError:
        continue

    for k in non_existing_keys:
      attr_type = definitions[k]

      if attr_type is None:
        self.__setattr__(k, None)
      elif isinstance(attr_type, (list, set, tuple, dict)) and len(attr_type) == 0:
        self.__setattr__(k, attr_type.__class__())
      elif isinstance(attr_type, (list, set, tuple)) and self._isclass(attr_type[0], BaseView):
        self.__setattr__(k, attr_type.__class__())
      else:
        self.__setattr__(k, attr_type.__class__(attr_type))

    return self

  def serialize(self, null_values=False):
    """
    :type null_values bool
    :rtype: dict
    """
    ret = {}

    for property_dict in [self.__class__.__dict__, self.__dict__]:
      for k in property_dict.keys():
        if k[:1] == "_" or (property_dict[k] is None and not null_values):
          continue

        v = property_dict[k]

        if isinstance(v, list):
          v_items = []
          for v_item in v:
            if self._isclass(v_item.__class__, BaseView):
              v_item_val = v_item.serialize(null_values=null_values)
              if not null_values and len(v_item_val) == 0:
                continue
              v_items.append(v_item_val)
            elif self._isclass(v_item, BaseView):  # when were passed Class instead of instance
              pass
            else:
              v_items.append(v_item)

          ret[k] = v_items
        elif self._isclass(v.__class__, BaseView):
          ret[k] = v.serialize(null_values=null_values)
        elif self._isclass(v, BaseView):  # when were passed Class instead of instance
          pass
        else:
          ret[k] = v

    return ret